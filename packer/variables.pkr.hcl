variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "project_name" {
  type    = string
  default = "course-management"
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}

# Optional. If you don't have a default VPC or need to build inside your Terraform VPC,
# pass a public subnet id here.
variable "subnet_id" {
  type    = string
  default = null
}

# Optional. If empty, Packer will create a temporary SG.
variable "vpc_id" {
  type    = string
  default = null
}

# Optional. Provide your own SG if needed.
variable "security_group_id" {
  type    = string
  default = null
}
