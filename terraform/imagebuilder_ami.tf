###############################################
# Build AMI via Terraform (EC2 Image Builder)
#
# Usage:
# - Set use_imagebuilder_ami=true
# - Bump imagebuilder_version to force a new AMI build
# - Apply; Terraform will build the AMI and wire it into the launch template
###############################################

data "aws_caller_identity" "current" {}

data "archive_file" "course_app_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../app"
  output_path = "${path.module}/course-app.zip"
}

resource "aws_s3_bucket" "imagebuilder_artifacts" {
  count  = var.use_imagebuilder_ami ? 1 : 0
  bucket = "${lower(var.project_name)}-${lower(var.environment)}-ami-artifacts-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name      = "${var.project_name}-${var.environment}-ami-artifacts"
    Component = "imagebuilder"
  }
}

resource "aws_s3_bucket_public_access_block" "imagebuilder_artifacts" {
  count                   = var.use_imagebuilder_ami ? 1 : 0
  bucket                  = aws_s3_bucket.imagebuilder_artifacts[0].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_object" "course_app_zip" {
  count  = var.use_imagebuilder_ami ? 1 : 0
  bucket = aws_s3_bucket.imagebuilder_artifacts[0].id
  key    = "artifacts/${var.project_name}/${var.environment}/${var.imagebuilder_version}/course-app.zip"
  source = data.archive_file.course_app_zip.output_path
  etag   = filemd5(data.archive_file.course_app_zip.output_path)
}

resource "aws_s3_object" "course_app_requirements" {
  count  = var.use_imagebuilder_ami ? 1 : 0
  bucket = aws_s3_bucket.imagebuilder_artifacts[0].id
  key    = "artifacts/${var.project_name}/${var.environment}/${var.imagebuilder_version}/requirements.txt"
  source = "${path.module}/../requirements.txt"
  etag   = filemd5("${path.module}/../requirements.txt")
}

# IAM role for Image Builder build instances
resource "aws_iam_role" "imagebuilder_instance_role" {
  count = var.use_imagebuilder_ami ? 1 : 0
  name  = "${var.project_name}-imagebuilder-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "sts:AssumeRole"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "imagebuilder_managed" {
  count      = var.use_imagebuilder_ami ? 1 : 0
  role       = aws_iam_role.imagebuilder_instance_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/EC2InstanceProfileForImageBuilder"
}

# Ensure the build instance remains a valid SSM managed instance.
# Some environments (e.g., SSM Quick Setup) may attempt to attach a default instance
# profile to instances that are not SSM-enabled, which can override the intended
# Image Builder instance profile and break builds.
resource "aws_iam_role_policy_attachment" "imagebuilder_ssm_core" {
  count      = var.use_imagebuilder_ami ? 1 : 0
  role       = aws_iam_role.imagebuilder_instance_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "imagebuilder_s3_read" {
  count = var.use_imagebuilder_ami ? 1 : 0
  name  = "${var.project_name}-imagebuilder-s3-${var.environment}"
  role  = aws_iam_role.imagebuilder_instance_role[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:GetObjectVersion", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.imagebuilder_artifacts[0].arn,
          "${aws_s3_bucket.imagebuilder_artifacts[0].arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_instance_profile" "imagebuilder_instance_profile" {
  count = var.use_imagebuilder_ami ? 1 : 0
  name  = "${var.project_name}-imagebuilder-profile-${var.environment}"
  role  = aws_iam_role.imagebuilder_instance_role[0].name
}

resource "aws_imagebuilder_infrastructure_configuration" "course_app" {
  count = var.use_imagebuilder_ami ? 1 : 0

  name                  = "${var.project_name}-${var.environment}-infra"
  instance_profile_name = aws_iam_instance_profile.imagebuilder_instance_profile[0].name

  instance_types = [var.imagebuilder_instance_type]

  subnet_id         = aws_subnet.public[0].id
  security_group_ids = [aws_security_group.ec2.id]

  terminate_instance_on_failure = true

  tags = {
    Name      = "${var.project_name}-${var.environment}-imagebuilder"
    Component = "imagebuilder"
  }
}

resource "aws_imagebuilder_component" "course_app" {
  count = var.use_imagebuilder_ami ? 1 : 0

  name     = "${var.project_name}-${var.environment}-course-app"
  platform = "Linux"
  version  = var.imagebuilder_version

  data = <<-YAML
    name: ${var.project_name}-${var.environment}-course-app
    description: Install Course Management app (FastAPI) and dependencies
    schemaVersion: 1.0
    phases:
      - name: build
        steps:
          - name: InstallPackages
            action: ExecuteBash
            inputs:
              commands:
                - dnf update -y
                - dnf install -y python3.11 python3.11-pip git wget unzip awscli
                - mkdir -p /opt/course-app/app
                - aws s3 cp s3://${aws_s3_bucket.imagebuilder_artifacts[0].bucket}/${aws_s3_object.course_app_zip[0].key} /tmp/course-app.zip
                - unzip -o /tmp/course-app.zip -d /opt/course-app/app
                - aws s3 cp s3://${aws_s3_bucket.imagebuilder_artifacts[0].bucket}/${aws_s3_object.course_app_requirements[0].key} /opt/course-app/requirements.txt
                - python3.11 -m venv /opt/course-app/.venv
                - /opt/course-app/.venv/bin/pip install --upgrade pip
                - /opt/course-app/.venv/bin/pip install -r /opt/course-app/requirements.txt
                - |
                  cat > /etc/systemd/system/course-app.service <<'EOF'
                  [Unit]
                  Description=Course Management FastAPI service
                  After=network.target

                  [Service]
                  Type=simple
                  User=ec2-user
                  WorkingDirectory=/opt/course-app
                  EnvironmentFile=/etc/course-app.env
                  Environment=PYTHONPATH=/opt/course-app
                  ExecStart=/opt/course-app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
                  StandardOutput=append:/var/log/course-app.log
                  StandardError=append:/var/log/course-app.log
                  Restart=always
                  RestartSec=10

                  [Install]
                  WantedBy=multi-user.target
                  EOF
                - |
                  cat > /etc/course-app.env <<'EOF'
                  AWS_REGION=${var.aws_region}
                  PORT=8000
                  EOF
                - systemctl daemon-reload
                - systemctl enable course-app.service
                - touch /var/log/course-app.log
                - chown -R ec2-user:ec2-user /opt/course-app
                - chown ec2-user:ec2-user /var/log/course-app.log
                - touch /opt/course-app/.prebaked
                - |
                  tmpdir=$(mktemp -d)
                  pushd "$tmpdir" >/dev/null
                  wget -q https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
                  rpm -U amazon-cloudwatch-agent.rpm
                  popd >/dev/null
                  rm -rf "$tmpdir"
  YAML
}

resource "aws_imagebuilder_image_recipe" "course_app" {
  count = var.use_imagebuilder_ami ? 1 : 0

  name         = "${var.project_name}-${var.environment}-recipe"
  version      = var.imagebuilder_version
  parent_image = data.aws_ami.amazon_linux_2023.id

  component {
    component_arn = aws_imagebuilder_component.course_app[0].arn
  }

  block_device_mapping {
    device_name = "/dev/xvda"

    ebs {
      volume_size           = 20
      volume_type           = "gp3"
      delete_on_termination = true
    }
  }
}

resource "aws_imagebuilder_distribution_configuration" "course_app" {
  count = var.use_imagebuilder_ami ? 1 : 0

  name = "${var.project_name}-${var.environment}-dist"

  distribution {
    region = var.aws_region

    ami_distribution_configuration {
      name        = "${var.project_name}-${var.environment}-{{ imagebuilder:buildDate }}"
      description = "${var.project_name} prebaked backend for ${var.environment}"

      ami_tags = {
        Name        = "${var.project_name}-${var.environment}-{{ imagebuilder:buildDate }}"
        Project     = var.project_name
        Environment = var.environment
        ManagedBy   = "terraform-imagebuilder"
        Component   = "backend"
        Version     = var.imagebuilder_version
      }
    }
  }
}

resource "aws_imagebuilder_image" "course_app" {
  count = var.use_imagebuilder_ami ? 1 : 0

  image_recipe_arn                 = aws_imagebuilder_image_recipe.course_app[0].arn
  infrastructure_configuration_arn = aws_imagebuilder_infrastructure_configuration.course_app[0].arn
  distribution_configuration_arn   = aws_imagebuilder_distribution_configuration.course_app[0].arn

  # Image build can take a while
  timeouts {
    create = "90m"
  }

  tags = {
    Name      = "${var.project_name}-${var.environment}-image"
    Component = "imagebuilder"
    Version   = var.imagebuilder_version
  }
}

locals {
  imagebuilder_ami_id = try(
    tolist(tolist(aws_imagebuilder_image.course_app[0].output_resources)[0].amis)[0].image,
    ""
  )
}
