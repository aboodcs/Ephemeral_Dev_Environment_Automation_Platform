#!/bin/bash

set -e

echo "====================================="
echo "Activity Detection Check"
echo "====================================="

RESULT="Allowed"

# Check Terraform state
echo "[1/3] Checking Terraform state..."

if aws s3 ls "s3://${TF_STATE_BUCKET}/${TF_STATE_KEY}" >/dev/null 2>&1; then
    echo "Terraform state exists."
else
    echo "No Terraform state found."
    echo "Environment probably does not exist."
    echo "STATUS=NOT_REQUIRED"
    exit 2
fi


# Check EC2 PreventDestroy tag

echo "[2/3] Checking EC2 PreventDestroy tag..."

INSTANCE_ID=$(aws ec2 describe-instances \
--filters \
"name=tag:Project,Values=${PROJECT_NAME}" \
"name=instance-state-name,Values=pending,running,stopping,stopped" \
--query "Reservations[].Instances[].InstanceId" \
--output text)


if [ "$INSTANCE_ID" != "None" ] && [ -n "$INSTANCE_ID" ]; then

    PROTECTED=$(aws ec2 describe-tags \
    --filters \
    "Name=resource-id,Values=${INSTANCE_ID}" \
    "Name=key,Values=PreventDestroy" \
    "Name=value,Values=true" \
    --query "Tags[].Value" \
    --output text)


    if [ "$PROTECTED" == "true" ]; then
        echo "BLOCKED: EC2 PreventDestroy=true detected."
        echo "STATUS=BLOCKED"
        exit 1
    fi

else
    echo "No matching EC2 instance found."
fi


# Check PR label

echo "[3/3] Checking Pull Request labels..."

PR_EXISTS=$(gh pr list \
--state open \
--label keep-dev-environment \
--json number \
--jq length)


if [ "$PR_EXISTS" -gt 0 ]; then
    echo "BLOCKED: Open PR contains keep-dev-environment label."
    echo "STATUS=BLOCKED"
    exit 1
fi


echo "All activity checks passed."
echo "STATUS=ALLOWED"

exit 0