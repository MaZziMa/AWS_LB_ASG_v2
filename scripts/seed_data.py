"""
Seed sample data to DynamoDB tables
"""
import boto3
from decimal import Decimal
import os
import sys
from typing import Any
dynamodb: Any = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))
from datetime import datetime
import uuid

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configuration
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev')
PROJECT_NAME = 'course-management'

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)

# Table names
COURSES_TABLE = f"{PROJECT_NAME}-courses-{ENVIRONMENT}"
STUDENTS_TABLE = f"{PROJECT_NAME}-students-{ENVIRONMENT}"
ENROLLMENTS_TABLE = f"{PROJECT_NAME}-enrollments-{ENVIRONMENT}"

# Sample data
SAMPLE_COURSES = [
    {
        'course_id': 'CS101',
        'title': 'Introduction to Python Programming',
        'description': 'Learn Python from scratch with hands-on projects',
        'instructor': 'Dr. Sarah Johnson',
        'duration_hours': 40,
        'price': Decimal('99.99'),
        'category': 'Programming',
        'created_at': datetime.utcnow().isoformat()
    },
    {
        'course_id': 'WEB201',
        'title': 'Full Stack Web Development',
        'description': 'Build modern web applications with React and Node.js',
        'instructor': 'Prof. Michael Chen',
        'duration_hours': 60,
        'price': Decimal('149.99'),
        'category': 'Web Development',
        'created_at': datetime.utcnow().isoformat()
    },
    {
        'course_id': 'DATA301',
        'title': 'Data Science with Python',
        'description': 'Master data analysis, visualization, and machine learning',
        'instructor': 'Dr. Emily Rodriguez',
        'duration_hours': 80,
        'price': Decimal('199.99'),
        'category': 'Data Science',
        'created_at': datetime.utcnow().isoformat()
    },
    {
        'course_id': 'AWS401',
        'title': 'AWS Cloud Architecture',
        'description': 'Design and deploy scalable applications on AWS',
        'instructor': 'John Smith, AWS Certified',
        'duration_hours': 50,
        'price': Decimal('179.99'),
        'category': 'Cloud Computing',
        'created_at': datetime.utcnow().isoformat()
    },
    {
        'course_id': 'AI501',
        'title': 'Artificial Intelligence Fundamentals',
        'description': 'Introduction to AI, ML, and Deep Learning concepts',
        'instructor': 'Dr. Lisa Wang',
        'duration_hours': 70,
        'price': Decimal('249.99'),
        'category': 'Artificial Intelligence',
        'created_at': datetime.utcnow().isoformat()
    }
]

SAMPLE_STUDENTS = [
    {
        'student_id': 'STU001',
        'name': 'Alice Anderson',
        'email': 'alice.anderson@email.com',
        'phone': '+1-555-0101',
        'created_at': datetime.utcnow().isoformat()
    },
    {
        'student_id': 'STU002',
        'name': 'Bob Baker',
        'email': 'bob.baker@email.com',
        'phone': '+1-555-0102',
        'created_at': datetime.utcnow().isoformat()
    },
    {
        'student_id': 'STU003',
        'name': 'Carol Chen',
        'email': 'carol.chen@email.com',
        'phone': '+1-555-0103',
        'created_at': datetime.utcnow().isoformat()
    },
    {
        'student_id': 'STU004',
        'name': 'David Davis',
        'email': 'david.davis@email.com',
        'phone': '+1-555-0104',
        'created_at': datetime.utcnow().isoformat()
    },
    {
        'student_id': 'STU005',
        'name': 'Emma Evans',
        'email': 'emma.evans@email.com',
        'phone': '+1-555-0105',
        'created_at': datetime.utcnow().isoformat()
    }
]

def seed_courses():
    """Seed courses table"""
    print(f"Seeding courses to table: {COURSES_TABLE}")
    table = dynamodb.Table(COURSES_TABLE)
    
    for course in SAMPLE_COURSES:
        try:
            table.put_item(Item=course)
            print(f"✓ Added course: {course['title']}")
        except Exception as e:
            print(f"✗ Error adding course {course['course_id']}: {str(e)}")

def seed_students():
    """Seed students table"""
    print(f"\nSeeding students to table: {STUDENTS_TABLE}")
    table = dynamodb.Table(STUDENTS_TABLE)
    
    for student in SAMPLE_STUDENTS:
        try:
            table.put_item(Item=student)
            print(f"✓ Added student: {student['name']}")
        except Exception as e:
            print(f"✗ Error adding student {student['student_id']}: {str(e)}")

def seed_enrollments():
    """Seed enrollments table"""
    print(f"\nSeeding enrollments to table: {ENROLLMENTS_TABLE}")
    table = dynamodb.Table(ENROLLMENTS_TABLE)
    
    # Create some sample enrollments
    enrollments = [
        {
            'enrollment_id': str(uuid.uuid4()),
            'student_id': 'STU001',
            'course_id': 'CS101',
            'enrolled_date': datetime.utcnow().isoformat(),
            'progress': 75,
            'completed': False,
            'created_at': datetime.utcnow().isoformat()
        },
        {
            'enrollment_id': str(uuid.uuid4()),
            'student_id': 'STU001',
            'course_id': 'WEB201',
            'enrolled_date': datetime.utcnow().isoformat(),
            'progress': 100,
            'completed': True,
            'created_at': datetime.utcnow().isoformat()
        },
        {
            'enrollment_id': str(uuid.uuid4()),
            'student_id': 'STU002',
            'course_id': 'CS101',
            'enrolled_date': datetime.utcnow().isoformat(),
            'progress': 50,
            'completed': False,
            'created_at': datetime.utcnow().isoformat()
        },
        {
            'enrollment_id': str(uuid.uuid4()),
            'student_id': 'STU003',
            'course_id': 'DATA301',
            'enrolled_date': datetime.utcnow().isoformat(),
            'progress': 30,
            'completed': False,
            'created_at': datetime.utcnow().isoformat()
        },
        {
            'enrollment_id': str(uuid.uuid4()),
            'student_id': 'STU004',
            'course_id': 'AWS401',
            'enrolled_date': datetime.utcnow().isoformat(),
            'progress': 60,
            'completed': False,
            'created_at': datetime.utcnow().isoformat()
        }
    ]
    
    for enrollment in enrollments:
        try:
            table.put_item(Item=enrollment)
            print(f"✓ Added enrollment: {enrollment['student_id']} -> {enrollment['course_id']}")
        except Exception as e:
            print(f"✗ Error adding enrollment: {str(e)}")

def main():
    """Main function"""
    print("=" * 50)
    print("Seeding DynamoDB Tables")
    print(f"Region: {AWS_REGION}")
    print(f"Environment: {ENVIRONMENT}")
    print("=" * 50)
    
    try:
        seed_courses()
        seed_students()
        seed_enrollments()
        
        print("\n" + "=" * 50)
        print("✓ Database seeding completed successfully!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n✗ Error during seeding: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
