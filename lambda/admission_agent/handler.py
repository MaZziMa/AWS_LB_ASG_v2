"""
HUTECH Admission Agent - Lambda Handler
Provides tools for admission consultation chatbot
"""
import boto3
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, List

from boto3.dynamodb.conditions import Attr

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

# Environment variables
ADMISSIONS_TABLE = os.environ.get('ADMISSIONS_TABLE', 'hutech-admissions')
KB_BUCKET = os.environ.get('KB_BUCKET', 'hutech-admission-kb')

def lambda_handler(event, context):
    """Main handler for Bedrock Agent action group"""
    try:
        logger.info(f"Event: {json.dumps(event)}")
        
        action_group = event.get('actionGroup', '')
        function = event.get('function', '')
        parameters = event.get('parameters', [])
        
        # Route to appropriate function
        if function == 'get_program_admission_info':
            return get_program_admission_info(parameters)
        elif function == 'compare_programs':
            return compare_programs(parameters)
        elif function == 'get_registration_links':
            return get_registration_links(parameters)
        elif function == 'search_scholarship_info':
            return search_scholarship_info(parameters)
        else:
            return error_response(f"Unknown function: {function}")
            
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return error_response(str(e))


def get_program_admission_info(parameters) -> Dict[str, Any]:
    """
    Lấy thông tin tuyển sinh chi tiết của 1 ngành học
    
    Args:
        parameters: [{"name": "program_name", "value": "Công nghệ thông tin"}]
    
    Returns:
        Structured admission information
    """
    try:
        program_id = get_param_value(parameters, 'program_id', required=False)
        program_name = get_param_value(parameters, 'program_name', required=False)

        if not program_id and not program_name:
            return error_response('Missing required parameter: program_name or program_id')
        
        table = dynamodb.Table(ADMISSIONS_TABLE)
        
        program = None
        if program_id:
            item_resp = table.get_item(Key={'program_id': program_id})
            program = item_resp.get('Item')

        if not program and program_name:
            program = get_program_by_name(table, program_name)

        if not program:
            return {
                'statusCode': 404,
                'body': {
                    'message': f'Không tìm thấy thông tin tuyển sinh cho ngành "{program_name or program_id}".',
                    'suggestion': 'Vui lòng kiểm tra lại tên ngành hoặc liên hệ phòng tuyển sinh.'
                }
            }
        
        # Format response theo template agent yêu cầu
        return {
            'statusCode': 200,
            'body': {
                'program_name': program['program_name'],
                'program_code': program.get('program_code', ''),
                'description': program['description'],
                'admission_methods': program['admission_methods'],
                'scholarships': program['scholarships'],
                'documents_required': program['documents'],
                'deadlines': program['deadlines'],
                'tuition_fee': program.get('tuition_fee', 'Liên hệ phòng tài chính'),
                'registration_url': program['registration_url'],
                'contact_info': program.get('contact_info', {})
            }
        }
        
    except Exception as e:
        logger.error(f"Error in get_program_admission_info: {str(e)}")
        return error_response(str(e))


def compare_programs(parameters) -> Dict[str, Any]:
    """
    So sánh 2 ngành học về điều kiện tuyển, học phí, cơ hội nghề nghiệp
    
    Args:
        parameters: [
            {"name": "program1", "value": "Công nghệ thông tin"},
            {"name": "program2", "value": "Khoa học dữ liệu"}
        ]
    """
    try:
        program1_name = get_param_value(parameters, 'program1')
        program2_name = get_param_value(parameters, 'program2')
        
        table = dynamodb.Table(ADMISSIONS_TABLE)
        
        # Get both programs
        prog1 = get_program_by_name(table, program1_name)
        prog2 = get_program_by_name(table, program2_name)
        
        if not prog1 or not prog2:
            missing = []
            if not prog1:
                missing.append(program1_name)
            if not prog2:
                missing.append(program2_name)
            return error_response(f"Không tìm thấy: {', '.join(missing)}")
        
        # Compare
        comparison = {
            'program1': {
                'name': prog1['program_name'],
                'tuition_fee': prog1.get('tuition_fee', 'N/A'),
                'admission_score': prog1.get('admission_score_range', 'N/A'),
                'career_prospects': prog1.get('career_prospects', []),
                'key_subjects': prog1.get('key_subjects', [])
            },
            'program2': {
                'name': prog2['program_name'],
                'tuition_fee': prog2.get('tuition_fee', 'N/A'),
                'admission_score': prog2.get('admission_score_range', 'N/A'),
                'career_prospects': prog2.get('career_prospects', []),
                'key_subjects': prog2.get('key_subjects', [])
            },
            'similarities': extract_similarities(prog1, prog2),
            'differences': extract_differences(prog1, prog2)
        }
        
        return {
            'statusCode': 200,
            'body': comparison
        }
        
    except Exception as e:
        logger.error(f"Error in compare_programs: {str(e)}")
        return error_response(str(e))


def get_registration_links(parameters) -> Dict[str, Any]:
    """
    Lấy link đăng ký tuyển sinh và đặt lịch tư vấn
    
    Args:
        parameters: [{"name": "program_name", "value": "Công nghệ thông tin"}]
    """
    try:
        program_name = get_param_value(parameters, 'program_name', required=False)
        
        table = dynamodb.Table(ADMISSIONS_TABLE)
        
        if program_name:
            # Get specific program links
            program = get_program_by_name(table, program_name)
            if not program:
                return error_response(f"Không tìm thấy ngành {program_name}")
            
            return {
                'statusCode': 200,
                'body': {
                    'program_name': program['program_name'],
                    'registration_url': program['registration_url'],
                    'schedule_consultation_url': program.get('consultation_url', 'https://calendly.com/hutech-admission'),
                    'hotline': '028 5445 5555',
                    'email': 'tuyensinh@hutech.edu.vn'
                }
            }
        else:
            # General links
            return {
                'statusCode': 200,
                'body': {
                    'general_registration_url': 'https://tuyensinh.hutech.edu.vn/dang-ky',
                    'schedule_consultation_url': 'https://calendly.com/hutech-admission',
                    'hotline': '028 5445 5555',
                    'email': 'tuyensinh@hutech.edu.vn',
                    'facebook': 'https://facebook.com/tuyensinh.hutech',
                    'zalo': 'https://zalo.me/hutechadmission'
                }
            }
        
    except Exception as e:
        logger.error(f"Error in get_registration_links: {str(e)}")
        return error_response(str(e))


def search_scholarship_info(parameters) -> Dict[str, Any]:
    """
    Tìm kiếm thông tin học bổng
    
    Args:
        parameters: [{"name": "scholarship_type", "value": "tuyển sinh"}]
    """
    try:
        scholarship_type = get_param_value(parameters, 'scholarship_type', required=False)
        
        table = dynamodb.Table(ADMISSIONS_TABLE)
        
        # Get all programs and aggregate scholarships
        response = table.scan()
        all_scholarships = []
        
        for program in response.get('Items', []):
            for scholarship in program.get('scholarships', []):
                scholarship['program'] = program['program_name']
                if not scholarship_type or scholarship_type.lower() in scholarship['type'].lower():
                    all_scholarships.append(scholarship)
        
        return {
            'statusCode': 200,
            'body': {
                'scholarships': all_scholarships,
                'total_count': len(all_scholarships)
            }
        }
        
    except Exception as e:
        logger.error(f"Error in search_scholarship_info: {str(e)}")
        return error_response(str(e))


# Helper functions

def _normalize_parameters(parameters) -> Dict[str, Any]:
    if parameters is None:
        return {}
    if isinstance(parameters, dict):
        return parameters
    if isinstance(parameters, list):
        normalized: Dict[str, Any] = {}
        for param in parameters:
            if isinstance(param, dict) and 'name' in param:
                normalized[str(param.get('name'))] = param.get('value')
        return normalized
    return {}


def get_param_value(parameters, param_name: str, required: bool = True):
    """Extract parameter value from Bedrock-style list or dict payload."""
    normalized = _normalize_parameters(parameters)
    if param_name in normalized and normalized.get(param_name) is not None:
        return normalized.get(param_name)

    if required:
        raise ValueError(f"Missing required parameter: {param_name}")
    return None


def get_program_by_name(table, program_name: str) -> Dict:
    """Query program by name"""
    if not program_name:
        return None

    # First try DynamoDB 'contains' (case-sensitive)
    try:
        response = table.scan(FilterExpression=Attr('program_name').contains(program_name))
        items = response.get('Items', [])
        if items:
            return items[0]
    except Exception:
        pass

    # Fallback: case-insensitive search in Python (small tables)
    response = table.scan()
    needle = program_name.strip().lower()
    for item in response.get('Items', []):
        candidate = str(item.get('program_name', '')).lower()
        if needle and needle in candidate:
            return item

    return None


def extract_similarities(prog1: Dict, prog2: Dict) -> List[str]:
    """Extract similarities between 2 programs"""
    similarities = []
    
    # Compare tuition
    if prog1.get('tuition_fee') == prog2.get('tuition_fee'):
        similarities.append(f"Học phí tương đương: {prog1.get('tuition_fee')}")
    
    # Compare admission methods
    methods1 = set(m['method'] for m in prog1.get('admission_methods', []))
    methods2 = set(m['method'] for m in prog2.get('admission_methods', []))
    common_methods = methods1.intersection(methods2)
    if common_methods:
        similarities.append(f"Cùng hình thức tuyển: {', '.join(common_methods)}")
    
    return similarities


def extract_differences(prog1: Dict, prog2: Dict) -> List[str]:
    """Extract differences between 2 programs"""
    differences = []
    
    # Compare career prospects
    career1 = set(prog1.get('career_prospects', []))
    career2 = set(prog2.get('career_prospects', []))
    
    unique1 = career1 - career2
    unique2 = career2 - career1
    
    if unique1:
        differences.append(f"{prog1['program_name']}: {', '.join(list(unique1)[:3])}")
    if unique2:
        differences.append(f"{prog2['program_name']}: {', '.join(list(unique2)[:3])}")
    
    return differences


def error_response(message: str) -> Dict[str, Any]:
    """Standard error response"""
    return {
        'statusCode': 500,
        'body': {
            'error': message,
            'message': 'Đã xảy ra lỗi. Vui lòng thử lại sau.'
        }
    }
