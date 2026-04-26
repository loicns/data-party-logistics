#!/bin/bash
set -e

echo "Starting EC2 Provisioning for DPL Ingestion Server..."

# Ensure .ssh directory exists
mkdir -p ~/.ssh

# 1. Create a Key Pair and save it locally
echo "Creating Key Pair..."
aws ec2 create-key-pair \
    --key-name dpl-ingestion-key \
    --query 'KeyMaterial' \
    --output text \
    --profile dpl --region eu-west-3 > ~/.ssh/dpl-ingestion-key.pem

# Secure the key
chmod 400 ~/.ssh/dpl-ingestion-key.pem

# 2. Create a Security Group
echo "Creating Security Group..."
SG_ID=$(aws ec2 create-security-group \
    --group-name dpl-ingestion-sg \
    --description "Allow SSH for ingestion server" \
    --query 'GroupId' \
    --output text \
    --profile dpl --region eu-west-3)

# 3. Allow SSH (Port 22) from anywhere
echo "Authorizing SSH ingress..."
aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp \
    --port 22 \
    --cidr 0.0.0.0/0 \
    --profile dpl --region eu-west-3

# 4. Get the latest Ubuntu 24.04 AMI ID for eu-west-3
echo "Fetching latest Ubuntu 24.04 AMI..."
AMI_ID=$(aws ec2 describe-images \
    --owners 099720109477 \
    --filters "Name=name,Values=ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*" \
    --query 'sort_by(Images, &CreationDate)[-1].ImageId' \
    --output text \
    --profile dpl --region eu-west-3)

# 5. Launch the Free Tier t3.micro Instance
echo "Launching t3.micro instance (AMI: $AMI_ID)..."
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id $AMI_ID \
    --count 1 \
    --instance-type t3.micro \
    --key-name dpl-ingestion-key \
    --security-group-ids $SG_ID \
    --query 'Instances[0].InstanceId' \
    --output text \
    --profile dpl --region eu-west-3)

echo "Launched Instance: $INSTANCE_ID"
echo "Waiting for instance to be running (this may take a minute)..."

# 6. Wait for it to boot and get the Public IP
aws ec2 wait instance-running --instance-ids $INSTANCE_ID --profile dpl --region eu-west-3
PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text \
    --profile dpl --region eu-west-3)

echo ""
echo "================================================="
echo "✅ SUCCESS! Your ingestion server is ready."
echo "EC2 Instance ID: $INSTANCE_ID"
echo "EC2 Public IP:   $PUBLIC_IP"
echo "================================================="
echo ""
echo "To connect, run:"
echo "ssh -i ~/.ssh/dpl-ingestion-key.pem ubuntu@$PUBLIC_IP"
