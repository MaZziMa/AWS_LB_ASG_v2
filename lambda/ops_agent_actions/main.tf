# ==============================================================================
# Terraform - Bedrock Agent Action Group for DevOps Operations
# ==============================================================================

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ==============================================================================
# Variables
# ==============================================================================

variable "aws_region" {
  default = "us-east-1"
}

variable "ops_asg_name" {
  default = "course-management-asg-dev"
}

variable "ops_target_group_arn" {
  description = "Target Group ARN"
}

variable "ops_alb_arn" {
  description = "ALB ARN"
}

variable "ops_ddb_tables" {
  default = "course-management-courses-dev,course-management-enrollments-dev,course-management-students-dev"
}

variable "api_base_url" {
  default = "http://localhost:8000"
}

variable "ops_log_groups" {
  description = "Comma-separated CloudWatch Log Group names for RCA queries (optional)"
  default     = ""
}

variable "bedrock_agent_id" {
  default = "CGWF5H93V2"
  description = "Existing Bedrock Agent ID"
}

# ==============================================================================
# IAM Role for Lambda
# ==============================================================================

resource "aws_iam_role" "lambda_role" {
  name = "ops-agent-actions-lambda-role"

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

resource "aws_iam_role_policy" "lambda_policy" {
  name = "ops-agent-actions-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "autoscaling:DescribeAutoScalingGroups",
          "autoscaling:DescribeInstanceRefreshes",
          "autoscaling:DescribeScalingActivities",
          "autoscaling:StartInstanceRefresh"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "elasticloadbalancing:DescribeTargetHealth",
          "elasticloadbalancing:DescribeLoadBalancers",
          "elasticloadbalancing:DescribeTargetGroups"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:GetMetricData",
          "cloudwatch:DescribeAlarms"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:DescribeTable"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:StartQuery",
          "logs:GetQueryResults",
          "logs:DescribeLogGroups"
        ]
        Resource = "*"
      }
    ]
  })
}

# ==============================================================================
# Lambda Function
# ==============================================================================

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/handler.py"
  output_path = "${path.module}/ops_agent_actions.zip"
}

resource "aws_lambda_function" "ops_agent_actions" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "ops-agent-actions"
  role             = aws_iam_role.lambda_role.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime          = "python3.11"
  timeout          = 30
  memory_size      = 256

  environment {
    variables = {
      OPS_ASG_NAME         = var.ops_asg_name
      OPS_TARGET_GROUP_ARN = var.ops_target_group_arn
      OPS_ALB_ARN          = var.ops_alb_arn
      OPS_DDB_TABLES       = var.ops_ddb_tables
      API_BASE_URL         = var.api_base_url
      OPS_LOG_GROUPS       = var.ops_log_groups
    }
  }
}

# ==============================================================================
# Lambda Permission for Bedrock Agent
# ==============================================================================

resource "aws_lambda_permission" "bedrock_invoke" {
  statement_id  = "AllowBedrockAgentInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ops_agent_actions.function_name
  principal     = "bedrock.amazonaws.com"
  source_arn    = "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:agent/${var.bedrock_agent_id}"
}

data "aws_caller_identity" "current" {}

# ==============================================================================
# Outputs
# ==============================================================================

output "lambda_arn" {
  value       = aws_lambda_function.ops_agent_actions.arn
  description = "Lambda ARN to use in Bedrock Action Group"
}

output "lambda_function_name" {
  value       = aws_lambda_function.ops_agent_actions.function_name
  description = "Lambda function name"
}

output "next_steps" {
  value = <<-EOT
    
    ✅ Lambda deployed: ${aws_lambda_function.ops_agent_actions.function_name}
    
    Next steps:
    1. Go to Bedrock Console → Agents → ${var.bedrock_agent_id}
    2. Edit in Agent Builder → Action groups → Add
    3. Name: devops-operations
    4. Lambda: ${aws_lambda_function.ops_agent_actions.function_name}
    5. Upload openapi_schema.json
    6. Prepare the agent
    7. Create/update Alias
    
  EOT
}
