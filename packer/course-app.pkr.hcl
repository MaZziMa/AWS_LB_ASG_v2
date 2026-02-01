packer {
  required_version = ">= 1.10.0"

  required_plugins {
    amazon = {
      version = ">= 1.2.0"
      source  = "github.com/hashicorp/amazon"
    }
  }
}

locals {
  timestamp = formatdate("YYYYMMDDhhmmss", timestamp())
  ami_name  = "${var.project_name}-${var.environment}-${local.timestamp}"
}

source "amazon-ebs" "course_app" {
  region                  = var.aws_region
  instance_type           = var.instance_type
  ssh_username            = "ec2-user"
  ami_name                = local.ami_name
  ami_description         = "${var.project_name} FastAPI backend prebaked for ${var.environment}"
  associate_public_ip_address = true

  subnet_id               = var.subnet_id
  vpc_id                  = var.vpc_id
  security_group_id       = var.security_group_id

  source_ami_filter {
    filters = {
      name                = "al2023-ami-2023*-x86_64"
      virtualization-type = "hvm"
      architecture        = "x86_64"
    }
    owners      = ["amazon"]
    most_recent = true
  }

  launch_block_device_mappings {
    device_name = "/dev/xvda"
    volume_size = 20
    volume_type = "gp3"
    delete_on_termination = true
  }

  tags = {
    Name        = local.ami_name
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "packer"
    Component   = "backend"
  }
}

build {
  name    = "${var.project_name}-prebaked"
  sources = ["source.amazon-ebs.course_app"]

  provisioner "file" {
    source      = "${path.root}/../app"
    destination = "/tmp/app"
  }

  provisioner "file" {
    source      = "${path.root}/../requirements.txt"
    destination = "/tmp/requirements.txt"
  }

  provisioner "shell" {
    script = "${path.root}/scripts/install_app.sh"
    environment_vars = [
      "APP_NAME=${var.project_name}",
      "ENVIRONMENT=${var.environment}",
      "APP_PORT=8000"
    ]
  }
}
