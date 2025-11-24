SHELL := /bin/bash

.PHONY: help install test lint format run docker-up docker-down deploy destroy clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install Python dependencies
	pip install -r requirements.txt

test: ## Run tests with coverage
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term

lint: ## Run code quality checks
	black --check app/ tests/
	flake8 app/ tests/ --max-line-length=100
	mypy app/ --ignore-missing-imports

format: ## Format code with black
	black app/ tests/

run: ## Run FastAPI application locally
	python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

docker-build: ## Build Docker image
	docker build -t course-management-app:latest .

docker-up: ## Start Docker Compose services
	docker-compose up -d

docker-down: ## Stop Docker Compose services
	docker-compose down

docker-logs: ## View Docker Compose logs
	docker-compose logs -f

terraform-init: ## Initialize Terraform
	cd terraform && terraform init

terraform-plan: ## Run Terraform plan
	cd terraform && terraform plan

terraform-apply: ## Apply Terraform changes
	cd terraform && terraform apply

terraform-destroy: ## Destroy Terraform infrastructure
	cd terraform && terraform destroy

seed: ## Seed database with sample data
	python scripts/seed_data.py

deploy: ## Deploy to AWS
	bash scripts/deploy.sh

destroy: ## Destroy AWS infrastructure
	bash scripts/destroy.sh

clean: ## Clean up generated files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info

all: install lint test ## Install dependencies, run linting and tests
