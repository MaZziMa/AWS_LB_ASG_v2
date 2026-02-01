output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "alb_arn" {
  description = "ARN of the Application Load Balancer"
  value       = aws_lb.main.arn
}

output "target_group_arn" {
  description = "ARN of the target group"
  value       = aws_lb_target_group.app.arn
}

output "asg_name" {
  description = "Name of the Auto Scaling Group"
  value       = aws_autoscaling_group.app.name
}

output "dynamodb_courses_table" {
  description = "Name of the courses DynamoDB table"
  value       = aws_dynamodb_table.courses.name
}

output "dynamodb_students_table" {
  description = "Name of the students DynamoDB table"
  value       = aws_dynamodb_table.students.name
}

output "dynamodb_enrollments_table" {
  description = "Name of the enrollments DynamoDB table"
  value       = aws_dynamodb_table.enrollments.name
}

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "application_url" {
  description = "URL to access the application"
  value       = "http://${aws_lb.main.dns_name}"
}

output "imagebuilder_ami_id" {
  description = "AMI ID built by EC2 Image Builder (when use_imagebuilder_ami=true)"
  value       = var.use_imagebuilder_ami ? local.imagebuilder_ami_id : null
}
