terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Backend removed for now to use default local state. Add an s3 backend later for team workflows.
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "Course-Management-System"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}
