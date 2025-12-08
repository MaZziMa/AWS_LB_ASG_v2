# ALB/ASG Bedrock Assistant – Project Summary

## 1. Executive Overview
- **Purpose**: Deliver a packaged AWS reference architecture that combines customer-facing load-balanced auto scaling workloads with a Bedrock-powered RAG assistant for internal ops teams.
- **Scope**: Covers infrastructure (ALB, ASG, EC2, DynamoDB), automation (Terraform, GitHub Actions, Packer), data exports, and the `/ops/ask` RAG service layer.
- **Outcomes**: Faster deployments, elastic customer traffic handling, and faster incident/root-cause investigation via knowledge-backed Q&A.

## 2. Core Architecture (Customer Layer)
- **Traffic Flow**: Internet → Application Load Balancer → Target Group → Auto Scaling Group (FastAPI on EC2) → DynamoDB.
- **Resilience**: Multi-AZ ALB, ASG warm pools, health checks on `/health`, CloudWatch metrics/alarms, blue/green or rolling updates via ASG refresh.
- **Performance**: AMI prebaked with dependencies (Packer) keeps boot <2 minutes; ASG policies (`min=2`, `max=10`, target CPU 70%) limit latency spikes.
- **Security**: IAM least-privilege roles, SG chaining (ALB SG → EC2 SG), TLS termination at ALB, DynamoDB encryption at rest.

## 3. Operations Intelligence (RAG Layer)
- **Data Sources**: ALB access logs, ASG scaling history, CloudWatch alarms, runbooks/SOPs, incident retrospectives.
- **Storage & Prep**: Normalized JSONL/Markdown stored under structured S3 prefixes (`bedrock/logs`, `bedrock/docs`, etc.); scripts in `scripts/` automate exports (`export_asg_activities.py`, `upload_to_s3_for_bedrock.py`).
- **Knowledge Base**: Amazon Bedrock Knowledge Base handles ingestion, embedding, vector store, filtering via metadata (`component`, `severity`).
- **Serving Path**: FastAPI router `/ops/ask` retrieves top chunks from Bedrock KB, feeds them to Bedrock models (Claude/Llama/Titan) or OpenAI fallback, and returns answers + provenance.

## 4. Automation & Tooling
- **Infrastructure as Code**: Terraform modules for VPC, ALB, ASG, DynamoDB, IAM; variables file controls region/instance sizes.
- **CI/CD**: GitHub Actions workflow → lint/test → build Docker → push to ECR → Terraform apply → ASG instance refresh + health validation.
- **Imaging**: Packer template builds hardened AMIs with FastAPI app, systemd unit, CloudWatch agent.
- **Local Dev**: Docker Compose, `.venv`, pytest suite, Locust scripts for synthetic load.

## 5. Business Value & Commercialization
- **Customer-Facing Reliability**: ALB/ASG blueprint can be resold as a managed foundation for any API/monolith needing elastic scale.
- **Ops Efficiency**: Bedrock RAG shortens incident triage by grounding answers in real telemetry/runbooks; acts as differentiator vs. plain hosting.
- **Cost Envelope**: Demo configuration costs ~$50–115/month (2×t3.micro, 1 ALB, DynamoDB on-demand, CloudWatch).
- **Packaging**: Offer tiers (Core Load-Balanced Stack, +RAG add-on, Managed Ops) leveraging same codebase.

## 6. Recommended Next Steps
1. Finalize documentation scrub (ensure all references use "ALB/ASG Bedrock Assistant").
2. Enable continuous ingestion jobs so new logs/docs automatically sync to S3 prefixes.
3. Expand `/ops/ask` responses with remediation playbooks and Slack/Webhook notifications.
4. Prepare marketing/demo assets (diagrams, video walkthrough) based on this summary.
