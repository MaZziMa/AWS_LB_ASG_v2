"""
Unit tests for main application
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
import os

# Set test environment variables
os.environ["AWS_REGION"] = "us-east-1"
os.environ["COURSES_TABLE"] = "test-courses"
os.environ["STUDENTS_TABLE"] = "test-students"
os.environ["ENROLLMENTS_TABLE"] = "test-enrollments"

client = TestClient(app)


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert data["service"] == "course-management-system"


def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Course Management System API"
    assert "endpoints" in data
    assert data["version"] == "1.0.0"


def test_get_courses_endpoint_exists():
    """Test that courses endpoint exists"""
    response = client.get("/courses")
    # Should return 200 or 500 (if DynamoDB not configured in test)
    assert response.status_code in [200, 500]


def test_get_students_endpoint_exists():
    """Test that students endpoint exists"""
    response = client.get("/students")
    assert response.status_code in [200, 500]


def test_get_enrollments_endpoint_exists():
    """Test that enrollments endpoint exists"""
    response = client.get("/enrollments")
    assert response.status_code in [200, 500]


def test_api_documentation():
    """Test that OpenAPI documentation is available"""
    response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_schema():
    """Test that OpenAPI schema is available"""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "Course Management System"
