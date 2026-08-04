#!/usr/bin/env bash

set -euo pipefail

exec > >(tee -a /var/log/bootstrap.log) 2>&1
# ============================================
# Step-by-step explanation of the line below:
# ============================================
# 1) exec  → changes where ALL output of the script goes, from this point onward
# 2) >(tee -a /var/log/bootstrap.log)  → creates a pipe that sends output into the tee command
# 3) tee   → takes whatever it receives and sends it to TWO places at once:
#            - the screen (so you can watch it live)
#            - the log file (so it's saved for later)
# 4) -a    → append mode, adds to the file without erasing what was there before
# 5) 2>&1  → redirects error messages (stderr) to the same place as normal output (stdout)
#            so errors get printed AND logged too, not just regular messages
# ============================================
# End result: every output and error from the script shows on screen
# AND gets saved into /var/log/bootstrap.log at the same time
# ============================================

echo "Starting server bootstrap..."

KUBECTL_VERSION="v1.36.1"
KIND_VERSION="v0.32.0"

# ==========================================================
# AWS Configuration (Preserved for Migration Reference)
# ==========================================================
CLUSTER_NAME="ephemeral-dev-cluster"
NAMESPACE_NAME="ephemeral-dev"
DEPLOYMENT_NAME="aws-dev-env-app"
SERVICE_NAME="aws-dev-env-app-service"

# ==========================================================
# OCI Configuration
# ==========================================================
# CLUSTER_NAME="ephemeral-dev-cluster"
# NAMESPACE_NAME="ephemeral-dev"
# DEPLOYMENT_NAME="ephemeral-dev-app"
# SERVICE_NAME="ephemeral-dev-app-service"

HOST_PORT="80"

# ==========================================================
# Local Directories
# ==========================================================
KUBERNETES_DIRECTORY="/opt/ephemeral-dev/kubernetes"
SCRIPTS_DIRECTORY="/opt/ephemeral-dev/scripts"

KIND_CONFIG_PATH="${KUBERNETES_DIRECTORY}/kind-config.yaml"
NAMESPACE_PATH="${KUBERNETES_DIRECTORY}/namespace.yaml"
DEPLOYMENT_PATH="${KUBERNETES_DIRECTORY}/deployment.yaml"
SERVICE_PATH="${KUBERNETES_DIRECTORY}/service.yaml"
WAIT_SCRIPT_PATH="${SCRIPTS_DIRECTORY}/wait-for-application.sh"

# ==========================================================
# ec2-user kubeconfig destination
# ==========================================================
EC2_USER_KUBE_DIR="/home/ec2-user/.kube"
EC2_USER_KUBECONFIG="${EC2_USER_KUBE_DIR}/config"

# ==========================================================
# GitHub Repository Files
# (Same repository used for both AWS and OCI implementations)
# ==========================================================
KIND_CONFIG_URL="https://raw.githubusercontent.com/aboodcs/Ephemeral_Dev_Environment_Automation_Platform/main/kubernetes/kind-config.yaml"
NAMESPACE_URL="https://raw.githubusercontent.com/aboodcs/Ephemeral_Dev_Environment_Automation_Platform/main/kubernetes/namespace.yaml"
DEPLOYMENT_URL="https://raw.githubusercontent.com/aboodcs/Ephemeral_Dev_Environment_Automation_Platform/main/kubernetes/deployment.yaml"
SERVICE_URL="https://raw.githubusercontent.com/aboodcs/Ephemeral_Dev_Environment_Automation_Platform/main/kubernetes/service.yaml"
WAIT_SCRIPT_URL="https://raw.githubusercontent.com/aboodcs/Ephemeral_Dev_Environment_Automation_Platform/main/scripts/wait-for-application.sh"

echo "Installing required packages..."

dnf update -y --allowerasing

dnf install -y \
    docker \
    git \
    tar \
    gzip

echo "Enabling Docker..."

systemctl enable --now docker

echo "Checking Docker..."

systemctl status docker --no-pager

echo "Adding ec2-user to Docker group..."

usermod -aG docker ec2-user

echo "Creating project directories..."

mkdir -p "${KUBERNETES_DIRECTORY}"
mkdir -p "${SCRIPTS_DIRECTORY}"

echo "Installing kubectl ${KUBECTL_VERSION}..."

curl -fLo /usr/local/bin/kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl"

chmod +x /usr/local/bin/kubectl

echo "Installing kind ${KIND_VERSION}..."

curl -fLo /usr/local/bin/kind "https://kind.sigs.k8s.io/dl/${KIND_VERSION}/kind-linux-amd64"

chmod +x /usr/local/bin/kind

echo "Checking versions..."

kubectl version --client
kind version

echo "Downloading kind config..."

curl -fLo "${KIND_CONFIG_PATH}" "${KIND_CONFIG_URL}"

echo "Downloading Kubernetes namespace..."

curl -fLo "${NAMESPACE_PATH}" "${NAMESPACE_URL}"

echo "Downloading Kubernetes Deployment..."

curl -fLo "${DEPLOYMENT_PATH}" "${DEPLOYMENT_URL}"

echo "Downloading Kubernetes Service..."

curl -fLo "${SERVICE_PATH}" "${SERVICE_URL}"

echo "Downloading health-check script..."

curl -fLo "${WAIT_SCRIPT_PATH}" "${WAIT_SCRIPT_URL}"

chmod +x "${WAIT_SCRIPT_PATH}"

echo "Preparing ec2-user kubeconfig directory..."

# Create the destination directory up front and write kind's kubeconfig
# directly there via KUBECONFIG. This avoids relying on \$HOME (which is
# often unset/incorrect when this script runs as root via user-data),
# so we no longer depend on /root/.kube/config existing at all.
mkdir -p "${EC2_USER_KUBE_DIR}"

echo "Create a kind cluster..."
KUBECONFIG="${EC2_USER_KUBECONFIG}" kind create cluster \
  --name "${CLUSTER_NAME}" \
  --config "${KIND_CONFIG_PATH}" \
  --wait 120s

echo "Fixing ownership of ec2-user kubeconfig..."
chown -R ec2-user:ec2-user "${EC2_USER_KUBE_DIR}"
chmod 600 "${EC2_USER_KUBECONFIG}"

# Root also needs a working kubeconfig for the rest of this script
# (kubectl apply / logs / etc. below run as root), so point root's
# KUBECONFIG at the same file explicitly rather than assuming
# /root/.kube/config exists.
export KUBECONFIG="${EC2_USER_KUBECONFIG}"

echo "Creating namespace..."

kubectl apply -f "${NAMESPACE_PATH}"

echo "Creating Deployment..."

kubectl apply -f "${DEPLOYMENT_PATH}"

echo "Creating Service..."

kubectl apply -f "${SERVICE_PATH}"

echo "Waiting for Kubernetes and the application..."

if ! "${WAIT_SCRIPT_PATH}" \
  "http://localhost:${HOST_PORT}/" \
  30 \
  5; then
# URL:          http://localhost:80/
# Attempts:     30
# Wait:         5 seconds between attempts
# Maximum wait: approximately 150 seconds
  echo "ERROR: Kubernetes application failed to become ready."

  kubectl get pods \
    --namespace "${NAMESPACE_NAME}" \
    -o wide || true

  kubectl get service \
    "${SERVICE_NAME}" \
    --namespace "${NAMESPACE_NAME}" || true

  kubectl logs \
    deployment/"${DEPLOYMENT_NAME}" \
    --namespace "${NAMESPACE_NAME}" \
    --all-containers=true || true

  exit 1
fi
## exit 0 its mean the script is success
## exit 1 its mean the script is failed