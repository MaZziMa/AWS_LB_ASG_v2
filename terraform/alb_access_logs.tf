# =============================================================================
# ALB Access Logs Configuration
# =============================================================================
# This file enables ALB access logs to S3, with automatic ingestion to 
# CloudWatch Logs via Lambda for AIOps integration.
# =============================================================================

# Get ELB service account (aws_caller_identity.current is defined in imagebuilder_ami.tf)
data "aws_elb_service_account" "main" {}

# -----------------------------------------------------------------------------
# S3 Bucket for ALB Access Logs
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "alb_logs" {
  bucket = "${var.project_name}-alb-logs-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name    = "${var.project_name}-alb-logs-${var.environment}"
    Purpose = "ALB Access Logs"
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle policy to auto-delete old logs (keep 7 days for dev)
resource "aws_s3_bucket_lifecycle_configuration" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id

  rule {
    id     = "expire-old-logs"
    status = "Enabled"

    expiration {
      days = var.environment == "prod" ? 30 : 7
    }

    filter {
      prefix = "alb-logs/"
    }
  }
}

# S3 bucket policy - ALB needs permission to write logs
resource "aws_s3_bucket_policy" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowALBLogDelivery"
        Effect = "Allow"
        Principal = {
          AWS = data.aws_elb_service_account.main.arn
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.alb_logs.arn}/alb-logs/*"
      },
      {
        Sid    = "AllowALBLogDeliveryAcl"
        Effect = "Allow"
        Principal = {
          Service = "delivery.logs.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.alb_logs.arn}/alb-logs/*"
        Condition = {
          StringEquals = {
            "s3:x-amz-acl" = "bucket-owner-full-control"
          }
        }
      },
      {
        Sid    = "AllowLogDeliveryServiceGetBucketAcl"
        Effect = "Allow"
        Principal = {
          Service = "delivery.logs.amazonaws.com"
        }
        Action   = "s3:GetBucketAcl"
        Resource = aws_s3_bucket.alb_logs.arn
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# CloudWatch Log Group for ALB Logs
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "alb_access_logs" {
  name              = "/aws/alb/${var.project_name}-${var.environment}"
  retention_in_days = var.environment == "prod" ? 30 : 7

  tags = {
    Name    = "${var.project_name}-alb-logs-${var.environment}"
    Purpose = "ALB-Access-Logs-Ingested-from-S3"
  }
}

# -----------------------------------------------------------------------------
# Lambda Function to Ingest ALB Logs
# -----------------------------------------------------------------------------
data "archive_file" "alb_log_ingest" {
  type        = "zip"
  source_file = "${path.module}/../lambda/alb_log_ingest/handler.py"
  output_path = "${path.module}/alb_log_ingest.zip"
}

resource "aws_lambda_function" "alb_log_ingest" {
  filename         = data.archive_file.alb_log_ingest.output_path
  function_name    = "${var.project_name}-alb-log-ingest-${var.environment}"
  role             = aws_iam_role.alb_log_ingest.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.alb_log_ingest.output_base64sha256
  runtime          = "python3.11"
  timeout          = 60
  memory_size      = 256

  environment {
    variables = {
      LOG_GROUP_NAME = aws_cloudwatch_log_group.alb_access_logs.name
      REGION         = var.aws_region
    }
  }

  tags = {
    Name = "${var.project_name}-alb-log-ingest-${var.environment}"
  }
}

# IAM Role for Lambda
resource "aws_iam_role" "alb_log_ingest" {
  name = "${var.project_name}-alb-log-ingest-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Lambda permissions: CloudWatch Logs
resource "aws_iam_role_policy" "alb_log_ingest_logs" {
  name = "cloudwatch-logs"
  role = aws_iam_role.alb_log_ingest.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = [
          "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/*",
          "${aws_cloudwatch_log_group.alb_access_logs.arn}:*"
        ]
      }
    ]
  })
}

# Lambda permissions: S3 read
resource "aws_iam_role_policy" "alb_log_ingest_s3" {
  name = "s3-read"
  role = aws_iam_role.alb_log_ingest.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.alb_logs.arn,
          "${aws_s3_bucket.alb_logs.arn}/*"
        ]
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# S3 Event Notification → Lambda
# -----------------------------------------------------------------------------
resource "aws_lambda_permission" "alb_log_ingest_s3" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.alb_log_ingest.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.alb_logs.arn
}

resource "aws_s3_bucket_notification" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.alb_log_ingest.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "alb-logs/"
    filter_suffix       = ".log.gz"
  }

  depends_on = [aws_lambda_permission.alb_log_ingest_s3]
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------
output "alb_logs_bucket" {
  description = "S3 bucket for ALB access logs"
  value       = aws_s3_bucket.alb_logs.id
}

output "alb_logs_cloudwatch_group" {
  description = "CloudWatch Log Group for ALB access logs (for AIOps)"
  value       = aws_cloudwatch_log_group.alb_access_logs.name
}
