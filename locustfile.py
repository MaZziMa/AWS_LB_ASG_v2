"""
Locust load testing file for Course Management System API
Run with: locust --host=http://your-alb-dns-name.amazonaws.com
"""
from locust import HttpUser, task, between
import random


class CourseManagementUser(HttpUser):
    """Simulates user behavior for Course Management API"""
    
    # Wait 1-3 seconds between tasks
    wait_time = between(1, 3)
    
    # Sample data for testing
    course_ids = ["CS101", "WEB201", "DATA301", "AWS401", "AI501"]
    student_ids = ["STU001", "STU002", "STU003", "STU004", "STU005"]
    
    def on_start(self):
        """Called when a simulated user starts"""
        print("Starting load test...")
    
    @task(5)
    def check_health(self):
        """Health check endpoint - most frequent"""
        self.client.get("/health")
    

    
    @task(3)
    def get_course_by_id(self):
        """Get specific course by ID"""
        course_id = random.choice(self.course_ids)
        with self.client.get(f"/courses/{course_id}", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # Expected for non-existent courses
                response.success()
            else:
                response.failure(f"Got status {response.status_code}")
    
    @task(8)
    def get_all_students(self):
        """Get all students"""
        with self.client.get("/students", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status {response.status_code}")
    
    @task(2)
    def get_student_by_id(self):
        """Get specific student by ID"""
        student_id = random.choice(self.student_ids)
        with self.client.get(f"/students/{student_id}", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                response.success()
            else:
                response.failure(f"Got status {response.status_code}")
    
    @task(5)
    def get_all_enrollments(self):
        """Get all enrollments"""
        with self.client.get("/enrollments", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status {response.status_code}")
    
    @task(2)
    def get_student_enrollments(self):
        """Get enrollments for a specific student"""
        student_id = random.choice(self.student_ids)
        with self.client.get(f"/students/{student_id}/enrollments", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                response.success()
            else:
                response.failure(f"Got status {response.status_code}")
    
    @task(1)
    def create_course(self):
        """Create new course - less frequent write operation"""
        course_data = {
            "course_id": f"TEST{random.randint(1000, 9999)}",
            "title": f"Test Course {random.randint(1, 100)}",
            "description": "Load test course",
            "instructor": "Test Instructor",
            "duration_hours": random.randint(10, 100),
            "price": round(random.uniform(99.99, 999.99), 2),
            "category": random.choice(["Programming", "Cloud", "Data Science", "AI"])
        }
        with self.client.post("/courses", json=course_data, catch_response=True) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Got status {response.status_code}")

   


class PeakLoadUser(HttpUser):
    """Simulates peak load scenarios - read-heavy traffic"""
    
    wait_time = between(0.5, 1.5)
    

    
    @task(10)
    def rapid_health_checks(self):
        """Rapid health checks"""
        self.client.get("/health")
    
    @task(5)
    def rapid_student_access(self):
        """Rapid student access"""
        self.client.get("/students")

