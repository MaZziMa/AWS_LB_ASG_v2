#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="/opt/course-app"
SRC_APP="/tmp/app"
SRC_REQUIREMENTS="/tmp/requirements.txt"
PYTHON_BIN="python3.11"
SERVICE_FILE="/etc/systemd/system/course-app.service"
ENV_FILE="/etc/course-app.env"

sudo dnf update -y
sudo dnf install -y ${PYTHON_BIN} ${PYTHON_BIN}-pip git wget

sudo mkdir -p "${APP_ROOT}"
sudo rm -rf "${APP_ROOT}/app"
sudo cp -r "${SRC_APP}" "${APP_ROOT}/app"
sudo cp "${SRC_REQUIREMENTS}" "${APP_ROOT}/requirements.txt"

sudo ${PYTHON_BIN} -m venv "${APP_ROOT}/.venv"
sudo "${APP_ROOT}/.venv/bin/pip" install --upgrade pip
sudo "${APP_ROOT}/.venv/bin/pip" install -r "${APP_ROOT}/requirements.txt"

cat <<'EOF' | sudo tee "${ENV_FILE}"
AWS_REGION=us-east-1
COURSES_TABLE=placeholder
STUDENTS_TABLE=placeholder
ENROLLMENTS_TABLE=placeholder
APP_PORT=8000
EOF

sudo tee "${SERVICE_FILE}" > /dev/null <<'EOF'
[Unit]
Description=Course Management FastAPI service
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/course-app
EnvironmentFile=/etc/course-app.env
Environment=PYTHONPATH=/opt/course-app
ExecStart=/opt/course-app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable course-app.service

sudo chown -R ec2-user:ec2-user "${APP_ROOT}"
sudo rm -rf "${SRC_APP}" "${SRC_REQUIREMENTS}"
sudo touch "${APP_ROOT}/.prebaked"

tmpdir=$(mktemp -d)
pushd "${tmpdir}" >/dev/null
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
sudo rpm -U amazon-cloudwatch-agent.rpm
popd >/dev/null
rm -rf "${tmpdir}"
sudo mkdir -p /opt/aws/amazon-cloudwatch-agent/etc

echo "Prebaked AMI ready with application stack"
