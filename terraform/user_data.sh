#!/bin/bash
# User data script for EC2 instances with Bedrock Agent integration
set -e

APP_ROOT="/opt/course-app"
PREBAKED_FLAG="$APP_ROOT/.prebaked"
ENV_FILE="/etc/course-app.env"
CLOUDWATCH_CONFIG="/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json"

write_env_file() {
    # Best-effort: capture AMI_ID at boot via IMDS (doesn't require AWS API perms)
    AMI_ID_BOOT=""
    if command -v curl >/dev/null 2>&1; then
        AMI_ID_BOOT=$(curl -fsS --max-time 1 http://169.254.169.254/latest/dynamic/instance-identity/document 2>/dev/null | grep -oE '"imageId"\s*:\s*"ami-[a-z0-9]+"' | head -n1 | cut -d'"' -f4 || true)
    fi

    cat > "$ENV_FILE" << EOF
AWS_REGION=${aws_region}
COURSES_TABLE=${courses_table}
STUDENTS_TABLE=${students_table}
ENROLLMENTS_TABLE=${enrollments_table}
APP_PORT=${app_port}
APP_VERSION=1.0.0
AMI_ID=$AMI_ID_BOOT
OPS_ASG_NAME=${ops_asg_name}
OPS_TARGET_GROUP_ARN=${ops_target_group_arn}
OPS_ALB_ARN=${ops_alb_arn}
CUSTOMER_AGENT_ID=${customer_agent_id}
CUSTOMER_AGENT_ALIAS_ID=${customer_agent_alias}
OPS_AGENT_ID=${ops_agent_id}
OPS_AGENT_ALIAS_ID=${ops_agent_alias}
ENABLE_DYNAMODB=${enable_dynamodb}
CLOUDWATCH_LOG_GROUP=/aws/ec2/${project_name}-${environment}
AWS_ACCOUNT_ID=171308902397
EOF
}

write_cloudwatch_config() {
    mkdir -p "$(dirname "$CLOUDWATCH_CONFIG")"
    cat > "$CLOUDWATCH_CONFIG" << EOF
{
    "logs": {
        "logs_collected": {
            "files": {
                "collect_list": [
                    {
                        "file_path": "/var/log/course-app.log",
                        "log_group_name": "/aws/ec2/${project_name}-${environment}",
                        "log_stream_name": "{instance_id}/app"
                    },
                    {
                        "file_path": "/var/log/messages",
                        "log_group_name": "/aws/ec2/${project_name}-${environment}",
                        "log_stream_name": "{instance_id}/messages"
                    },
                    {
                        "file_path": "/var/log/cloud-init.log",
                        "log_group_name": "/aws/ec2/${project_name}-${environment}",
                        "log_stream_name": "{instance_id}/cloud-init"
                    },
                    {
                        "file_path": "/var/log/cloud-init-output.log",
                        "log_group_name": "/aws/ec2/${project_name}-${environment}",
                        "log_stream_name": "{instance_id}/cloud-init-output"
                    },
                    {
                        "file_path": "/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log",
                        "log_group_name": "/aws/ec2/${project_name}-${environment}",
                        "log_stream_name": "{instance_id}/cw-agent"
                    }
                ]
            }
        }
    }
}
EOF
}

echo "Starting application setup..."

# Fast path: AMI baked by Packer
if [ -f "$PREBAKED_FLAG" ]; then
    echo "Pre-baked image detected; configuring runtime env and starting service."

    write_env_file
    write_cloudwatch_config

    if [ -x /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl ]; then
        /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
            -a fetch-config \
            -m ec2 \
            -s \
            -c file:"$CLOUDWATCH_CONFIG" || true
    fi

    systemctl daemon-reload || true
    systemctl enable course-app.service || true
    systemctl restart course-app.service || true
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
mkdir -p $APP_ROOT/app
cd $APP_ROOT

# Create environment file
write_env_file

# Create requirements.txt
cat > requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
boto3==1.29.7
python-json-logger==2.0.7
EOF

# Install Python dependencies
python3.11 -m pip install --no-cache-dir -r requirements.txt

# Create bedrock_kb.py
cat > app/bedrock_kb.py << 'EOFBEDROCK'
"""
Bedrock Integration: Agents + Knowledge Bases
Routes customer/ops queries to respective Bedrock Agents with KB access
"""
import os
import logging
import boto3
import uuid
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Initialize Bedrock Agent Runtime client
bedrock_agent_runtime = boto3.client(
    "bedrock-agent-runtime", region_name=os.getenv("AWS_REGION", "us-east-1")
)

# Agent IDs from environment
CUSTOMER_AGENT_ID = os.getenv("CUSTOMER_AGENT_ID", "LJCIO6MTHB")
OPS_AGENT_ID = os.getenv("OPS_AGENT_ID", "CGWF5H93V2")
CUSTOMER_AGENT_ALIAS_ID = os.getenv("CUSTOMER_AGENT_ALIAS_ID", "IQQLSGF6X8")
OPS_AGENT_ALIAS_ID = os.getenv("OPS_AGENT_ALIAS_ID", "WX8RSD82ZC")


def invoke_agent(
    agent_id: str,
    query: str,
    session_id: Optional[str] = None,
    alias_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Invoke a Bedrock Agent with event stream parsing
    
    Args:
        agent_id: Bedrock Agent ID
        query: User's question
        session_id: Optional session ID for conversation continuity
        alias_id: Agent alias ID (DRAFT if not specified)
    
    Returns:
        dict with 'answer', 'session_id', 'agent_id'
    """
    try:
        # Generate or reuse session ID
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Default to DRAFT alias if not specified
        if not alias_id:
            alias_id = "TSTALIASID"
        
        logger.info(f"Invoking agent {agent_id} with alias {alias_id}")
        
        # Invoke agent
        response = bedrock_agent_runtime.invoke_agent(
            agentId=agent_id,
            agentAliasId=alias_id,
            sessionId=session_id,
            inputText=query,
        )
        
        # Parse EventStream response
        completion = ""
        event_count = 0
        
        for event in response.get("completion", []):
            event_count += 1
            
            # Extract chunk bytes
            if "chunk" in event:
                chunk = event["chunk"]
                if "bytes" in chunk:
                    chunk_text = chunk["bytes"].decode("utf-8")
                    completion += chunk_text
        
        logger.info(f"Agent {agent_id} returned {len(completion)} characters")
        
        return {
            "answer": completion.strip(),
            "session_id": session_id,
            "agent_id": agent_id,
        }
    
    except Exception as e:
        logger.error(f"Agent invocation error: {str(e)}")
        raise


def invoke_customer_agent(query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Invoke customer support agent (HUTECH info, courses, enrollment)"""
    return invoke_agent(
        agent_id=CUSTOMER_AGENT_ID,
        query=query,
        session_id=session_id,
        alias_id=CUSTOMER_AGENT_ALIAS_ID,
    )


def invoke_ops_agent(query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Invoke ops agent (ALB, ASG, deployments, incidents)"""
    return invoke_agent(
        agent_id=OPS_AGENT_ID,
        query=query,
        session_id=session_id,
        alias_id=OPS_AGENT_ALIAS_ID,
    )
EOFBEDROCK

# Create __init__.py
touch app/__init__.py

# Create main.py
cat > app/main.py << 'EOFMAIN'
"""
Course Management System - Main Application
FastAPI application with Bedrock Agent integration
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
import socket
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Course Management System",
    description="Learning platform with Bedrock Agents",
    version="2.0.0",
)

# Bedrock Agent integration
try:
    from app.bedrock_kb import invoke_customer_agent, invoke_ops_agent

    class AgentQuery(BaseModel):
        question: str
        session_id: Optional[str] = None

    @app.post("/api/customer/ask")
    async def ask_customer_agent(query: AgentQuery):
        """Query customer support agent (HUTECH, courses, enrollment)"""
        try:
            result = invoke_customer_agent(query.question, query.session_id)
            return result
        except Exception as e:
            logger.error(f"Customer Agent error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/ops/ask")
    async def ask_ops_agent(query: AgentQuery):
        """Query ops agent (ALB, ASG, deployments)"""
        try:
            result = invoke_ops_agent(query.question, query.session_id)
            return result
        except Exception as e:
            logger.error(f"Ops Agent error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    logger.info("Bedrock Agents enabled")
except Exception as e:
    logger.warning(f"Bedrock Agents not available: {str(e)}")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check(request: Request):
    """Health check endpoint for ALB target group"""
    hostname = socket.gethostname()
    client_ip = request.client.host if request.client else "unknown"
    logger.info("Health check served")
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "course-management-bedrock",
        "instance_id": hostname,
        "client_ip": client_ip,
    }

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Course Management System with Bedrock Agents",
        "version": "2.0.0",
        "endpoints": {
            "health": "/health",
            "customer_agent": "/api/customer/ask",
            "ops_agent": "/api/ops/ask",
        },
    }

@app.get("/cpu-burn")
async def cpu_burn(duration: int = 30):
    """Burn CPU for testing auto-scaling"""
    import time
    start_time = time.time()
    end_time = start_time + duration
    
    iterations = 0
    while time.time() < end_time:
        _ = sum(i * i for i in range(1000))
        iterations += 1
    
    elapsed = time.time() - start_time
    return {
        "message": f"CPU burn completed",
        "duration_requested": duration,
        "duration_actual": round(elapsed, 2),
        "iterations": iterations,
    }
EOFMAIN

# Configure CloudWatch agent
cat > "$CLOUDWATCH_CONFIG" << EOFCW
{
    "logs": {
        "logs_collected": {
            "files": {
                "collect_list": [
                    {
                        "file_path": "/var/log/course-app.log",
                        "log_group_name": "/aws/ec2/${project_name}-${environment}",
                        "log_stream_name": "{instance_id}/app"
                    },
                    {
                        "file_path": "/var/log/messages",
                        "log_group_name": "/aws/ec2/${project_name}-${environment}",
                        "log_stream_name": "{instance_id}/messages"
                    },
                    {
                        "file_path": "/var/log/cloud-init.log",
                        "log_group_name": "/aws/ec2/${project_name}-${environment}",
                        "log_stream_name": "{instance_id}/cloud-init"
                    },
                    {
                        "file_path": "/var/log/cloud-init-output.log",
                        "log_group_name": "/aws/ec2/${project_name}-${environment}",
                        "log_stream_name": "{instance_id}/cloud-init-output"
                    },
                    {
                        "file_path": "/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log",
                        "log_group_name": "/aws/ec2/${project_name}-${environment}",
                        "log_stream_name": "{instance_id}/cw-agent"
                    }
                ]
            }
        }
    }
}
EOFCW

# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -s \
    -c file:"$CLOUDWATCH_CONFIG"

# Create systemd service
cat > /etc/systemd/system/course-app.service << EOFSVC
[Unit]
Description=Course Management System with Bedrock Agents
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_ROOT
EnvironmentFile=$ENV_FILE
ExecStart=/usr/bin/python3.11 -m uvicorn app.main:app --host 0.0.0.0 --port ${app_port}
Restart=always
RestartSec=10
StandardOutput=append:/var/log/course-app.log
StandardError=append:/var/log/course-app.log

[Install]
WantedBy=multi-user.target
EOFSVC

# Start the application
systemctl daemon-reload
systemctl enable course-app.service
systemctl start course-app.service

echo "Application setup completed successfully"
