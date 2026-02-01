#!/bin/bash
# User data script for EC2 instances
set -e

APP_ROOT="/opt/course-app"
PREBAKED_FLAG="$APP_ROOT/.prebaked"
ENV_FILE="/etc/course-app.env"
CLOUDWATCH_CONFIG="/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json"

if [ -f "$PREBAKED_FLAG" ]; then
    echo "Pre-baked image detected; skipping bootstrap install."

    cat > "$ENV_FILE" << EOF
AWS_REGION="${aws_region}"
COURSES_TABLE="${courses_table}"
STUDENTS_TABLE="${students_table}"
ENROLLMENTS_TABLE="${enrollments_table}"
APP_PORT="${app_port}"
EOF

    cat > "$CLOUDWATCH_CONFIG" << 'EOF'
{
    "logs": {
        "logs_collected": {
            "files": {
                "collect_list": [
                    {
                        "file_path": "/var/log/messages",
                        "log_group_name": "/aws/ec2/${project_name}-${environment}",
                        "log_stream_name": "{instance_id}/messages"
                    }
                ]
            }
        }
    }
}
EOF

    /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
        -a fetch-config \
        -m ec2 \
        -s \
        -c file:"$CLOUDWATCH_CONFIG"

    systemctl daemon-reload
    systemctl enable course-app
    systemctl restart course-app
    echo "Pre-baked init completed"
    exit 0
fi

# Update system
dnf update -y

# Install Python 3.11 and development tools
dnf install -y python3.11 python3.11-pip git

# Install and configure CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
rpm -U ./amazon-cloudwatch-agent.rpm

# Create application directory
mkdir -p /opt/course-app
cd /opt/course-app

# Clone application code (replace with your repository)
# For now, we'll create the application files directly
cat > /opt/course-app/requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
boto3==1.29.7
mangum==0.17.0
python-json-logger==2.0.7
EOF

# Install Python dependencies
python3.11 -m pip install -r requirements.txt

# Create main application file
cat > /opt/course-app/main.py << 'EOFAPP'
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import boto3
from decimal import Decimal
import os
import logging
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from time import perf_counter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Course Management System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION', '${aws_region}'))
COURSES_TABLE = os.getenv('COURSES_TABLE', '${courses_table}')
STUDENTS_TABLE = os.getenv('STUDENTS_TABLE', '${students_table}')
ENROLLMENTS_TABLE = os.getenv('ENROLLMENTS_TABLE', '${enrollments_table}')

class Course(BaseModel):
    course_id: str
    title: str
    description: str
    instructor: str
    duration_hours: int
    price: float
    category: str

class Student(BaseModel):
    student_id: str
    name: str
    email: str
    phone: Optional[str] = None

class Enrollment(BaseModel):
    enrollment_id: str
    student_id: str
    course_id: str
    enrolled_date: str
    progress: int = 0
    completed: bool = False

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/")
async def root():
    return {"message": "Course Management System", "version": "1.0.0", "cpu_burn": "/cpu-burn"}

@app.get("/courses")
async def get_courses():
    try:
        table = dynamodb.Table(COURSES_TABLE)
        response = table.scan()
        courses = response.get('Items', [])
        for course in courses:
            for key, value in course.items():
                if isinstance(value, Decimal):
                    course[key] = float(value)
        return {"courses": courses, "count": len(courses)}
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/courses/{course_id}")
async def get_course(course_id: str):
    try:
        table = dynamodb.Table(COURSES_TABLE)
        response = table.get_item(Key={'course_id': course_id})
        if 'Item' not in response:
            raise HTTPException(status_code=404, detail="Course not found")
        course = response['Item']
        for key, value in course.items():
            if isinstance(value, Decimal):
                course[key] = float(value)
        return course
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/courses")
async def create_course(course: Course):
    try:
        table = dynamodb.Table(COURSES_TABLE)
        item = course.dict()
        item['created_at'] = datetime.utcnow().isoformat()
        if isinstance(item.get('price'), float):
            from decimal import Decimal as _D
            item['price'] = _D(str(item['price']))
        table.put_item(Item=item)
        return {"message": "Course created successfully", "course": course}
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/students")
async def get_students():
    try:
        table = dynamodb.Table(STUDENTS_TABLE)
        response = table.scan()
        students = response.get('Items', [])
        return {"students": students, "count": len(students)}
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/students/{student_id}")
async def get_student(student_id: str):
    try:
        table = dynamodb.Table(STUDENTS_TABLE)
        response = table.get_item(Key={'student_id': student_id})
        if 'Item' not in response:
            raise HTTPException(status_code=404, detail="Student not found")
        return response['Item']
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/students")
async def create_student(student: Student):
    try:
        table = dynamodb.Table(STUDENTS_TABLE)
        item = student.dict()
        item['created_at'] = datetime.utcnow().isoformat()
        table.put_item(Item=item)
        return {"message": "Student created successfully", "student": student}
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/enrollments")
async def get_enrollments():
    try:
        table = dynamodb.Table(ENROLLMENTS_TABLE)
        response = table.scan()
        enrollments = response.get('Items', [])
        for enrollment in enrollments:
            for key, value in enrollment.items():
                if isinstance(value, Decimal):
                    enrollment[key] = float(value)
        return {"enrollments": enrollments, "count": len(enrollments)}
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/enrollments")
async def create_enrollment(enrollment: Enrollment):
    try:
        table = dynamodb.Table(ENROLLMENTS_TABLE)
        item = enrollment.dict()
        item['created_at'] = datetime.utcnow().isoformat()
        table.put_item(Item=item)
        return {"message": "Enrollment created successfully", "enrollment": enrollment}
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/students/{student_id}/enrollments")
async def get_student_enrollments(student_id: str):
    try:
        table = dynamodb.Table(ENROLLMENTS_TABLE)
        response = table.scan(
            FilterExpression='student_id = :sid',
            ExpressionAttributeValues={':sid': student_id}
        )
        enrollments = response.get('Items', [])
        for enrollment in enrollments:
            for key, value in enrollment.items():
                if isinstance(value, Decimal):
                    enrollment[key] = float(value)
        return {"enrollments": enrollments, "count": len(enrollments)}
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cpu-burn")
async def cpu_burn(iterations: int = 50000000):
    bounded = max(1, min(iterations, 200000000))
    start = perf_counter()
    accumulator = 0
    for i in range(bounded):
        accumulator += (i % 5) * (i % 3)
    duration = perf_counter() - start
    return {
        "requested_iterations": iterations,
        "executed_iterations": bounded,
        "result": accumulator,
        "duration_seconds": round(duration, 3)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=${app_port})
EOFAPP

# Set environment variables
export AWS_REGION="${aws_region}"
export COURSES_TABLE="${courses_table}"
export STUDENTS_TABLE="${students_table}"
export ENROLLMENTS_TABLE="${enrollments_table}"

# Create systemd service
cat > /etc/systemd/system/course-app.service << 'EOF'
[Unit]
Description=Course Management System
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/course-app
Environment="AWS_REGION=${aws_region}"
Environment="COURSES_TABLE=${courses_table}"
Environment="STUDENTS_TABLE=${students_table}"
Environment="ENROLLMENTS_TABLE=${enrollments_table}"
ExecStart=/usr/bin/python3.11 -m uvicorn main:app --host 0.0.0.0 --port ${app_port}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Change ownership
chown -R ec2-user:ec2-user /opt/course-app

# Start and enable service
systemctl daemon-reload
systemctl enable course-app
systemctl start course-app

# Configure CloudWatch logs
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOF'
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/messages",
            "log_group_name": "/aws/ec2/${project_name}-${environment}",
            "log_stream_name": "{instance_id}/messages"
          }
        ]
      }
    }
  }
}
EOF

/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -s \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

echo "Setup completed successfully"
