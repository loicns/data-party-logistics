#!/bin/bash
set -euo pipefail

PROFILE="dpl"
REGION="eu-west-3"
KEY_NAME="dpl-ingestion-key"
KEY_PATH="$HOME/.ssh/${KEY_NAME}.pem"
SG_NAME="dpl-ingestion-sg"

echo "Starting EC2 Provisioning for DPL Ingestion Server..."

# Ensure .ssh directory exists
mkdir -p ~/.ssh

# 1. Create or reuse the SSH key pair
if [ -f "$KEY_PATH" ]; then
    echo "Local SSH key already exists at $KEY_PATH — reusing it."
    if ! aws ec2 describe-key-pairs \
        --key-names "$KEY_NAME" \
        --profile "$PROFILE" \
        --region "$REGION" >/dev/null 2>&1; then
        echo "ERROR: Local key exists, but AWS key pair '$KEY_NAME' does not."
        echo "Delete $KEY_PATH and recreate the key pair, or choose a new key name."
        exit 1
    fi
else
    if aws ec2 describe-key-pairs \
        --key-names "$KEY_NAME" \
        --profile "$PROFILE" \
        --region "$REGION" >/dev/null 2>&1; then
        echo "ERROR: AWS key pair '$KEY_NAME' already exists, but $KEY_PATH does not."
        echo "AWS cannot return the private key again after creation."
        echo "Delete the AWS key pair and rerun the script, or update the script to use a new key name."
        exit 1
    fi

    echo "Creating Key Pair..."
    TMP_KEY_PATH="$(mktemp)"
    aws ec2 create-key-pair \
        --key-name "$KEY_NAME" \
        --query 'KeyMaterial' \
        --output text \
        --profile "$PROFILE" \
        --region "$REGION" > "$TMP_KEY_PATH"

    mv "$TMP_KEY_PATH" "$KEY_PATH"
    chmod 400 "$KEY_PATH"
fi

# 2. Create or reuse the Security Group
SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=${SG_NAME}" \
    --query 'SecurityGroups[0].GroupId' \
    --output text \
    --profile "$PROFILE" \
    --region "$REGION")

if [ "$SG_ID" = "None" ]; then
    echo "Creating Security Group..."
    SG_ID=$(aws ec2 create-security-group \
        --group-name "$SG_NAME" \
        --description "Allow SSH for ingestion server" \
        --query 'GroupId' \
        --output text \
        --profile "$PROFILE" \
        --region "$REGION")

    echo "Authorizing SSH ingress..."
    aws ec2 authorize-security-group-ingress \
        --group-id "$SG_ID" \
        --protocol tcp \
        --port 22 \
        --cidr 0.0.0.0/0 \
        --profile "$PROFILE" \
        --region "$REGION"
else
    echo "Security Group already exists ($SG_ID) — reusing it."
fi

# 4. Get the latest Ubuntu 24.04 AMI ID for eu-west-3
echo "Fetching latest Ubuntu 24.04 AMI..."
AMI_ID=$(aws ec2 describe-images \
    --owners 099720109477 \
    --filters "Name=name,Values=ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*" \
    --query 'sort_by(Images, &CreationDate)[-1].ImageId' \
    --output text \
    --profile "$PROFILE" \
    --region "$REGION")

# 5. Launch the Free Tier t3.micro Instance
echo "Launching t3.micro instance (AMI: $AMI_ID)..."
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id $AMI_ID \
    --count 1 \
    --instance-type t3.micro \
    --key-name "$KEY_NAME" \
    --security-group-ids "$SG_ID" \
    --query 'Instances[0].InstanceId' \
    --output text \
    --profile "$PROFILE" \
    --region "$REGION")

echo "Launched Instance: $INSTANCE_ID"
echo "Waiting for instance to be running (this may take a minute)..."

# 6. Wait for it to boot and get the Public IP
aws ec2 wait instance-running \
    --instance-ids "$INSTANCE_ID" \
    --profile "$PROFILE" \
    --region "$REGION"
PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids "$INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text \
    --profile "$PROFILE" \
    --region "$REGION")

echo ""
echo "================================================="
echo "✅ SUCCESS! Your ingestion server is ready."
echo "EC2 Instance ID: $INSTANCE_ID"
echo "EC2 Public IP:   $PUBLIC_IP"
echo "================================================="
echo ""
echo "To connect, run:"
echo "ssh -i $KEY_PATH ubuntu@$PUBLIC_IP"
