#!/bin/bash
# Deploy script for Course Management System

set -e

echo "🚀 Starting deployment process..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
PROJECT_NAME="course-management"

# Functions
check_requirements() {
    echo "Checking requirements..."
    
    command -v terraform >/dev/null 2>&1 || { 
        echo -e "${RED}❌ Terraform is not installed${NC}"; 
        exit 1; 
    }
    
    command -v aws >/dev/null 2>&1 || { 
        echo -e "${RED}❌ AWS CLI is not installed${NC}"; 
        exit 1; 
    }
    
    echo -e "${GREEN}✅ All requirements satisfied${NC}"
}

deploy_infrastructure() {
    echo "📦 Deploying infrastructure with Terraform..."
    
    cd terraform
    
    # Initialize Terraform
    terraform init
    
    # Validate configuration
    terraform validate
    
    # Plan deployment
    terraform plan -out=tfplan
    
    # Apply changes
    read -p "Do you want to apply these changes? (yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
        terraform apply tfplan
        echo -e "${GREEN}✅ Infrastructure deployed successfully${NC}"
    else
        echo -e "${YELLOW}⚠️  Deployment cancelled${NC}"
        exit 0
    fi
    
    cd ..
}

get_outputs() {
    echo "📊 Getting infrastructure outputs..."
    
    cd terraform
    
    ALB_DNS=$(terraform output -raw alb_dns_name 2>/dev/null || echo "")
    ASG_NAME=$(terraform output -raw asg_name 2>/dev/null || echo "")
    
    cd ..
    
    if [ -n "$ALB_DNS" ]; then
        echo -e "${GREEN}✅ Application Load Balancer DNS: http://$ALB_DNS${NC}"
        echo "$ALB_DNS" > .alb_dns
    fi
    
    if [ -n "$ASG_NAME" ]; then
        echo -e "${GREEN}✅ Auto Scaling Group: $ASG_NAME${NC}"
    fi
}

seed_database() {
    echo "🌱 Seeding database with sample data..."
    
    python3 scripts/seed_data.py
    
    echo -e "${GREEN}✅ Database seeded${NC}"
}

health_check() {
    echo "🏥 Performing health check..."
    
    if [ -f .alb_dns ]; then
        ALB_DNS=$(cat .alb_dns)
        
        for i in {1..10}; do
            if curl -f "http://$ALB_DNS/health" 2>/dev/null; then
                echo -e "${GREEN}✅ Health check passed!${NC}"
                return 0
            fi
            echo "Attempt $i/10 failed, retrying in 10 seconds..."
            sleep 10
        done
        
        echo -e "${RED}❌ Health check failed after 10 attempts${NC}"
        return 1
    else
        echo -e "${YELLOW}⚠️  ALB DNS not found, skipping health check${NC}"
    fi
}

# Main execution
main() {
    echo "=================================="
    echo "Course Management System Deployment"
    echo "Environment: $ENVIRONMENT"
    echo "Region: $AWS_REGION"
    echo "=================================="
    echo ""
    
    check_requirements
    deploy_infrastructure
    get_outputs
    
    echo ""
    echo "Waiting 60 seconds for instances to initialize..."
    sleep 60
    
    seed_database
    health_check
    
    echo ""
    echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
    
    if [ -f .alb_dns ]; then
        ALB_DNS=$(cat .alb_dns)
        echo ""
        echo "=================================="
        echo "Access your application at:"
        echo "http://$ALB_DNS"
        echo "API Documentation:"
        echo "http://$ALB_DNS/docs"
        echo "=================================="
    fi
}

# Run main function
main
