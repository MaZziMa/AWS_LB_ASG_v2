"""
Application Configuration
"""
import os
from typing import Optional

class Config:
    """Application configuration"""
    
    # AWS Configuration
    AWS_REGION: str = os.getenv('AWS_REGION', 'us-east-1')
    COURSES_TABLE: str = os.getenv('COURSES_TABLE', 'courses')
    STUDENTS_TABLE: str = os.getenv('STUDENTS_TABLE', 'students')
    ENROLLMENTS_TABLE: str = os.getenv('ENROLLMENTS_TABLE', 'enrollments')
    
    # Application Configuration
    APP_NAME: str = "Course Management System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Server Configuration
    HOST: str = os.getenv('HOST', '0.0.0.0')
    PORT: int = int(os.getenv('PORT', '8000'))
    
    # CORS Configuration
    ALLOWED_ORIGINS: list = os.getenv('ALLOWED_ORIGINS', '*').split(',')
    
    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')

config = Config()
