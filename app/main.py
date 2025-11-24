"""
Course Management System - Main Application
FastAPI application with DynamoDB integration
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import boto3
from decimal import Decimal
import os
import logging
import socket
from typing import List, Optional, Any
from pydantic import BaseModel
from datetime import datetime
from time import perf_counter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Course Management System",
    description="Learning platform with AWS Load Balancer and Auto Scaling",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DynamoDB setup
dynamodb: Any = boto3.resource(
    "dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1")
)
COURSES_TABLE = os.getenv("COURSES_TABLE", "courses")
STUDENTS_TABLE = os.getenv("STUDENTS_TABLE", "students")
ENROLLMENTS_TABLE = os.getenv("ENROLLMENTS_TABLE", "enrollments")


# Pydantic models
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


# Helper function to convert Decimal to float
def decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


# Health check endpoint for Load Balancer
@app.get("/health")
async def health_check(request: Request):
    """Health check endpoint for ALB target group"""
    hostname = socket.gethostname()
    client_ip = request.client.host if request.client else "unknown"
    logger.info(
        "Health check served", extra={"hostname": hostname, "client_ip": client_ip}
    )
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "course-management-system",
        "instance_id": hostname,
        "client_ip": client_ip,
    }


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Course Management System API",
        "version": "1.0.0",
        "endpoints": {
            "courses": "/courses",
            "students": "/students",
            "enrollments": "/enrollments",
            "health": "/health",
            "cpu_burn": "/cpu-burn",
        },
    }


# ============ COURSES ENDPOINTS ============
@app.get("/courses")
async def get_courses():
    """Get all courses"""
    try:
        table = dynamodb.Table(COURSES_TABLE)
        response = table.scan()
        courses = response.get("Items", [])

        # Convert Decimal to float for JSON serialization
        for course in courses:
            for key, value in course.items():
                if isinstance(value, Decimal):
                    course[key] = float(value)

        return {"courses": courses, "count": len(courses)}
    except Exception as e:
        logger.error(f"Error fetching courses: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/courses/{course_id}")
async def get_course(course_id: str):
    """Get a specific course by ID"""
    try:
        table = dynamodb.Table(COURSES_TABLE)
        response = table.get_item(Key={"course_id": course_id})

        if "Item" not in response:
            raise HTTPException(status_code=404, detail="Course not found")

        course = response["Item"]
        for key, value in course.items():
            if isinstance(value, Decimal):
                course[key] = float(value)

        return course
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching course: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/courses")
async def create_course(course: Course):
    """Create a new course"""
    try:
        table = dynamodb.Table(COURSES_TABLE)
        item = course.dict()
        item["created_at"] = datetime.utcnow().isoformat()
        # DynamoDB does not allow native Python float, convert to Decimal
        if isinstance(item.get("price"), float):
            # Use str() to avoid floating point representation issues
            item["price"] = Decimal(str(item["price"]))

        table.put_item(Item=item)
        # Convert back for response consistency
        response_course = course.dict()
        return {"message": "Course created successfully", "course": response_course}
    except Exception as e:
        logger.error(f"Error creating course: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/courses/{course_id}")
async def delete_course(course_id: str):
    """Delete a course"""
    try:
        table = dynamodb.Table(COURSES_TABLE)
        table.delete_item(Key={"course_id": course_id})
        return {"message": "Course deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting course: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ STUDENTS ENDPOINTS ============
@app.get("/students")
async def get_students():
    """Get all students"""
    try:
        table = dynamodb.Table(STUDENTS_TABLE)
        response = table.scan()
        students = response.get("Items", [])
        return {"students": students, "count": len(students)}
    except Exception as e:
        logger.error(f"Error fetching students: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/students/{student_id}")
async def get_student(student_id: str):
    """Get a specific student by ID"""
    try:
        table = dynamodb.Table(STUDENTS_TABLE)
        response = table.get_item(Key={"student_id": student_id})

        if "Item" not in response:
            raise HTTPException(status_code=404, detail="Student not found")

        return response["Item"]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching student: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/students")
async def create_student(student: Student):
    """Create a new student"""
    try:
        table = dynamodb.Table(STUDENTS_TABLE)
        item = student.dict()
        item["created_at"] = datetime.utcnow().isoformat()

        table.put_item(Item=item)
        return {"message": "Student created successfully", "student": student}
    except Exception as e:
        logger.error(f"Error creating student: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ ENROLLMENTS ENDPOINTS ============
@app.get("/enrollments")
async def get_enrollments():
    """Get all enrollments"""
    try:
        table = dynamodb.Table(ENROLLMENTS_TABLE)
        response = table.scan()
        enrollments = response.get("Items", [])

        # Convert Decimal to float
        for enrollment in enrollments:
            for key, value in enrollment.items():
                if isinstance(value, Decimal):
                    enrollment[key] = float(value)

        return {"enrollments": enrollments, "count": len(enrollments)}
    except Exception as e:
        logger.error(f"Error fetching enrollments: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/enrollments")
async def create_enrollment(enrollment: Enrollment):
    """Create a new enrollment"""
    try:
        table = dynamodb.Table(ENROLLMENTS_TABLE)
        item = enrollment.dict()
        item["created_at"] = datetime.utcnow().isoformat()

        table.put_item(Item=item)
        return {"message": "Enrollment created successfully", "enrollment": enrollment}
    except Exception as e:
        logger.error(f"Error creating enrollment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/enrollments/student/{student_id}")
async def get_student_enrollments(student_id: str):
    """Get all enrollments for a specific student"""
    try:
        table = dynamodb.Table(ENROLLMENTS_TABLE)
        response = table.scan(
            FilterExpression="student_id = :sid",
            ExpressionAttributeValues={":sid": student_id},
        )
        enrollments = response.get("Items", [])

        # Convert Decimal to float
        for enrollment in enrollments:
            for key, value in enrollment.items():
                if isinstance(value, Decimal):
                    enrollment[key] = float(value)

        return {"enrollments": enrollments, "count": len(enrollments)}
    except Exception as e:
        logger.error(f"Error fetching student enrollments: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cpu-burn")
async def cpu_burn(iterations: int = 50_000_000):
    """Artificially burn CPU cycles to test auto-scaling behavior."""
    try:
        # Bound iterations to avoid accidentally freezing the instance
        bounded_iterations = max(1, min(iterations, 200_000_000))
        start = perf_counter()
        accumulator = 0
        for i in range(bounded_iterations):
            accumulator += (i % 5) * (i % 3)
        duration = perf_counter() - start
        return {
            "requested_iterations": iterations,
            "executed_iterations": bounded_iterations,
            "result": accumulator,
            "duration_seconds": round(duration, 3),
        }
    except Exception as e:
        logger.error(f"Error during cpu-burn: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
