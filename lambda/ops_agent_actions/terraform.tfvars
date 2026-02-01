aws_region = "us-east-1"

ops_asg_name = "course-management-asg-dev"

ops_target_group_arn = "arn:aws:elasticloadbalancing:us-east-1:171308902397:targetgroup/course-management-tg-dev/d508f5b775f1fdaa"

ops_alb_arn = "arn:aws:elasticloadbalancing:us-east-1:171308902397:loadbalancer/app/course-management-alb-dev/2c94f5ca48d3f749"

ops_ddb_tables = "course-management-courses-dev,course-management-enrollments-dev,course-management-students-dev"

api_base_url = "http://course-management-alb-dev-1530526851.us-east-1.elb.amazonaws.com"

ops_log_groups = "/aws/ec2/course-management-dev,/aws/imagebuilder/course-management-dev-recipe,/aws/alb/course-management-dev"

bedrock_agent_id = "CGWF5H93V2"
