aws_region    = "us-east-1"
environment   = "dev"
project_name  = "course-management"
instance_type = "t3.micro"
min_size      = 2
max_size      = 5
desired_capacity        = 2
target_cpu_utilization  = 60
health_check_path       = "/health"
app_port                = 8000
# Leave blank to use the latest Amazon Linux 2023 AMI (or the Image Builder AMI when enabled).
custom_ami_id          = ""

# Use Terraform-managed AMI build (EC2 Image Builder) so deployed code matches this repo.
use_imagebuilder_ami    = true

# Bump this to force a new AMI build.
imagebuilder_version    = "1.0.6"
