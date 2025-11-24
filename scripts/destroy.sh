#!/bin/bash
# Destroy infrastructure script

set -e

echo "⚠️  WARNING: This will destroy all infrastructure!"
echo "Environment: ${ENVIRONMENT:-dev}"
echo ""

read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Destruction cancelled."
    exit 0
fi

echo "🔥 Destroying infrastructure..."

cd terraform

# Show what will be destroyed
terraform plan -destroy

# Confirm again
read -p "Proceed with destruction? (yes/no): " confirm2

if [ "$confirm2" = "yes" ]; then
    terraform destroy -auto-approve
    echo "✅ Infrastructure destroyed successfully"
else
    echo "Destruction cancelled."
fi

cd ..
