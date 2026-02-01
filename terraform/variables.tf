variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "course-management"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "min_size" {
  description = "Minimum number of instances in ASG"
  type        = number
  default     = 2
}

variable "max_size" {
  description = "Maximum number of instances in ASG"
  type        = number
  default     = 10
}

variable "desired_capacity" {
  description = "Desired number of instances in ASG"
  type        = number
  default     = 2
}

variable "target_cpu_utilization" {
  description = "Target CPU utilization for auto scaling"
  type        = number
  default     = 70
}

variable "health_check_path" {
  description = "Health check path for ALB"
  type        = string
  default     = "/health"
}

variable "app_port" {
  description = "Application port"
  type        = number
  default     = 8000
}

variable "custom_ami_id" {
  description = "Optional AMI ID for the launch template. Leave blank to use the latest Amazon Linux 2023 image."
  type        = string
  default     = ""
}

variable "use_imagebuilder_ami" {
  description = "When true, Terraform will build a new AMI via EC2 Image Builder and use it in the launch template (unless custom_ami_id is set)."
  type        = bool
  default     = false
}

variable "imagebuilder_version" {
  description = "Version for Image Builder resources/recipe. Bump this to force a new AMI build."
  type        = string
  default     = "1.0.0"
}

variable "imagebuilder_instance_type" {
  description = "Instance type used by the Image Builder build instance."
  type        = string
  default     = "t3.micro"
}
