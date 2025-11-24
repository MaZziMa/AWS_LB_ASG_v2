# Course Management System - AWS Load Balancing & Auto Scaling Demo

[![CI/CD Pipeline](https://github.com/yourusername/AWS_LB_ASG_v2/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/yourusername/AWS_LB_ASG_v2/actions)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-green.svg)](https://fastapi.tiangolo.com/)
[![Terraform](https://img.shields.io/badge/Terraform-1.6.0-purple.svg)](https://www.terraform.io/)

Hệ thống quản lý khóa học trực tuyến sử dụng AWS Load Balancer, Auto Scaling Group và DynamoDB. Dự án demo minh họa kiến trúc scalable, high-availability trên AWS.

## 🏗️ Kiến Trúc

```
Internet
    ↓
Application Load Balancer (ALB)
    ↓
Target Group
    ↓
Auto Scaling Group (2-10 EC2 instances)
    ↓
DynamoDB Tables:
├── Courses
├── Students
└── Enrollments
```

## ✨ Tính Năng

### Application Features
- ✅ RESTful API với FastAPI
- ✅ Auto-generated API documentation (Swagger/OpenAPI)
- ✅ CRUD operations cho Courses, Students, Enrollments
- ✅ Health check endpoint cho ALB
- ✅ Async/await support
- ✅ Pydantic data validation

### Infrastructure Features
- ✅ Application Load Balancer với health checks
- ✅ Auto Scaling Group với target tracking
- ✅ DynamoDB với Global Secondary Indexes
- ✅ CloudWatch monitoring và alarms
- ✅ VPC với public/private subnets
- ✅ Security Groups theo best practices
- ✅ IAM roles với least privilege

### DevOps Features
- ✅ GitHub Actions CI/CD pipeline
- ✅ Automated testing với pytest
- ✅ Code quality checks (black, flake8, mypy)
- ✅ Docker containerization
- ✅ Infrastructure as Code với Terraform
- ✅ Automated deployment scripts

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- AWS CLI configured
- Terraform 1.6.0+
- Docker (optional)
- Git

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/AWS_LB_ASG_v2.git
cd AWS_LB_ASG_v2
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Locally

```bash
# Set environment variables
export AWS_REGION=us-east-1
export COURSES_TABLE=courses
export STUDENTS_TABLE=students
export ENROLLMENTS_TABLE=enrollments

# Run application
python -m uvicorn app.main:app --reload
```

Truy cập: http://localhost:8000/docs

### 4. Run with Docker

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f app
```

### 5. Deploy to AWS

```bash
# Configure AWS credentials
aws configure

# Deploy infrastructure
cd terraform
terraform init
terraform plan
terraform apply

# Seed database (optional)
python scripts/seed_data.py

# Get application URL
terraform output alb_dns_name
```

### 6. (Optional) Build a Pre-baked AMI with Packer

Sử dụng thư mục `packer/` để tạo AMI đã chứa đầy đủ Python packages, mã nguồn và systemd service – giúp EC2 khởi động trong ~30-40 giây.

```bash
cd packer
packer init course-app.pkr.hcl
packer build \
    -var "project_name=course-management" \
    -var "environment=dev" \
    -var "aws_region=us-east-1" \
    course-app.pkr.hcl
```

Khi build thành công, Packer sẽ in ra `artifact_id` dạng `us-east-1:ami-xxxxxxxx`. Sao chép AMI ID đó sang Terraform bằng cách thêm vào `terraform.tfvars`:

```hcl
custom_ami_id = "ami-xxxxxxxx"
```

Mỗi lần rebuild AMI, chỉ cần cập nhật giá trị này rồi `terraform apply` + chạy Instance Refresh là toàn bộ ASG dùng image mới.

## 📁 Cấu Trúc Dự Án

```
AWS_LB_ASG_v2/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   └── config.py            # Configuration
├── terraform/
│   ├── main.tf              # Main Terraform configuration
│   ├── variables.tf         # Variables
│   ├── outputs.tf           # Outputs
│   ├── vpc.tf               # VPC resources
│   ├── alb.tf               # Load Balancer
│   ├── asg.tf               # Auto Scaling Group
│   ├── dynamodb.tf          # DynamoDB tables
│   └── user_data.sh         # EC2 initialization script
├── packer/
│   ├── course-app.pkr.hcl   # Packer template for prebaked AMI
│   └── scripts/
│       └── install_app.sh   # Provisioning logic inside AMI
├── .github/
│   └── workflows/
│       ├── ci-cd.yml        # Main CI/CD pipeline
│       └── terraform-plan.yml # Terraform plan on PR
├── scripts/
│   ├── deploy.sh            # Deployment script
│   ├── destroy.sh           # Cleanup script
│   └── seed_data.py         # Database seeding
├── tests/
│   └── test_main.py         # Unit tests
├── Dockerfile               # Development Dockerfile
├── Dockerfile.prod          # Production Dockerfile
├── docker-compose.yml       # Local development setup
├── requirements.txt         # Python dependencies
└── README.md
```

## 🔧 Configuration

### Terraform Variables

Tạo file `terraform/terraform.tfvars`:

```hcl
aws_region     = "us-east-1"
environment    = "dev"
instance_type  = "t3.micro"
min_size       = 2
max_size       = 10
desired_capacity = 2
target_cpu_utilization = 70
custom_ami_id = "" # hoặc "ami-xxxxxxxx" nếu dùng prebaked AMI
```

### Environment Variables

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# Application Configuration
COURSES_TABLE=course-management-courses-dev
STUDENTS_TABLE=course-management-students-dev
ENROLLMENTS_TABLE=course-management-enrollments-dev
DEBUG=false
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test
pytest tests/test_main.py::test_health_check -v
```

## 📊 API Documentation

Sau khi deploy, truy cập API documentation tại:
- Swagger UI: `http://<ALB_DNS>/docs`
- ReDoc: `http://<ALB_DNS>/redoc`
- OpenAPI JSON: `http://<ALB_DNS>/openapi.json`

### Main Endpoints

```
GET  /health                      # Health check
GET  /                            # API info
GET  /courses                     # List all courses
GET  /courses/{course_id}         # Get course by ID
POST /courses                     # Create new course
DELETE /courses/{course_id}       # Delete course
GET  /students                    # List all students
GET  /students/{student_id}       # Get student by ID
POST /students                    # Create new student
GET  /enrollments                 # List all enrollments
POST /enrollments                 # Create enrollment
GET  /enrollments/student/{id}    # Get student's enrollments
```

## 🔄 CI/CD Pipeline

GitHub Actions workflow tự động:

1. **Test Stage**
   - Code quality checks (black, flake8, mypy)
   - Unit tests với coverage
   - Generate coverage reports

2. **Build Stage**
   - Build Docker image
   - Push to Amazon ECR
   - Tag với commit SHA

3. **Deploy Stage**
   - Terraform plan và apply
   - Trigger ASG instance refresh
   - Health check validation

4. **Notify Stage**
   - Deployment status notification

## 📈 Monitoring

### CloudWatch Metrics

- CPU Utilization
- Network In/Out
- Request Count
- Target Response Time
- Healthy/Unhealthy Host Count

### CloudWatch Alarms

- High CPU (> 80%) → Scale Up
- Low CPU (< 20%) → Scale Down
- Unhealthy targets → SNS notification

### Logs

```bash
# View ALB logs
aws logs tail /aws/elasticloadbalancing/app/course-management-alb --follow

# View application logs
aws logs tail /aws/ec2/course-management --follow
```

## 🔒 Security Best Practices

- ✅ Security Groups với least privilege
- ✅ IAM roles thay vì hardcoded credentials
- ✅ VPC với public/private subnets
- ✅ DynamoDB encryption at rest
- ✅ ALB với HTTPS (cấu hình certificate)
- ✅ Non-root user trong Docker
- ✅ Secrets management với AWS Secrets Manager

## 💰 Cost Estimation

Ước tính chi phí hàng tháng (us-east-1):

| Service | Configuration | Monthly Cost |
|---------|--------------|--------------|
| EC2 (t3.micro) | 2-10 instances | $15-75 |
| Application Load Balancer | 1 ALB | $16 |
| DynamoDB | Pay-per-request | $1-10 |
| Data Transfer | ~100 GB | $9 |
| CloudWatch | Logs & Metrics | $5 |
| **Total** | | **~$46-115/month** |

## 🛠️ Troubleshooting

### Health Check Failed

```bash
# Check target health
aws elbv2 describe-target-health --target-group-arn <ARN>

# Check application logs
ssh ec2-user@<instance-ip>
sudo journalctl -u course-app -f
```

### Auto Scaling Issues

```bash
# Check ASG activity
aws autoscaling describe-scaling-activities --auto-scaling-group-name <name>

# Check CloudWatch alarms
aws cloudwatch describe-alarms --alarm-names <alarm-name>
```

### DynamoDB Access Denied

```bash
# Verify IAM role permissions
aws iam get-role-policy --role-name course-management-ec2-role --policy-name dynamodb-policy
```

## 📚 Learning Resources

- [AWS Load Balancing](https://aws.amazon.com/elasticloadbalancing/)
- [Auto Scaling Best Practices](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-best-practices.html)
- [DynamoDB Developer Guide](https://docs.aws.amazon.com/dynamodb/index.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👤 Author

Your Name - [@yourhandle](https://github.com/yourhandle)

## 🙏 Acknowledgments

- AWS Documentation
- FastAPI Community
- Terraform Community
- GitHub Actions

---

**⭐ Nếu project này hữu ích, hãy cho một star nhé!**
