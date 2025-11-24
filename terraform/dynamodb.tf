# Courses Table
resource "aws_dynamodb_table" "courses" {
  name           = "${var.project_name}-courses-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "course_id"

  attribute {
    name = "course_id"
    type = "S"
  }

  attribute {
    name = "category"
    type = "S"
  }

  global_secondary_index {
    name            = "CategoryIndex"
    hash_key        = "category"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name = "${var.project_name}-courses-${var.environment}"
  }
}

# Students Table
resource "aws_dynamodb_table" "students" {
  name           = "${var.project_name}-students-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "student_id"

  attribute {
    name = "student_id"
    type = "S"
  }

  attribute {
    name = "email"
    type = "S"
  }

  global_secondary_index {
    name            = "EmailIndex"
    hash_key        = "email"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name = "${var.project_name}-students-${var.environment}"
  }
}

# Enrollments Table
resource "aws_dynamodb_table" "enrollments" {
  name           = "${var.project_name}-enrollments-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "enrollment_id"

  attribute {
    name = "enrollment_id"
    type = "S"
  }

  attribute {
    name = "student_id"
    type = "S"
  }

  attribute {
    name = "course_id"
    type = "S"
  }

  global_secondary_index {
    name            = "StudentIndex"
    hash_key        = "student_id"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "CourseIndex"
    hash_key        = "course_id"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name = "${var.project_name}-enrollments-${var.environment}"
  }
}
