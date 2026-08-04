# Ephemeral Dev Environment Automation Platform

![AWS](https://img.shields.io/badge/AWS-EC2%20%7C%20VPC%20%7C%20S3-232F3E?style=for-the-badge&logo=amazon-aws&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-1.5+-844FBA?style=for-the-badge&logo=terraform&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-24.0+-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-kind-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-CI%2FCD-2088FF?style=for-the-badge&logo=github-actions&logoColor=white)
![Python](https://img.shields.io/badge/Python-Flask-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Slack](https://img.shields.io/badge/Slack-Notifications-4A154B?style=for-the-badge&logo=slack&logoColor=white)

An automated, self-destructing, enterprise-grade cloud infrastructure platform designed to provision ephemeral development environments on demand during working hours and tear them down automatically after working hours to drastically reduce AWS cloud infrastructure costs.

---

# 1. Project Overview

### What Problem This Solves
In modern cloud engineering, persistent development environments running 24/7 account for a massive portion of wasted cloud spending. Typical dev instances sit idle during nights, weekends, and non-working hours, accumulating unnecessary compute, storage, and networking charges.

### Why Ephemeral Environments Are Useful
Ephemeral development environments solve idle cloud costs by adopting disposable, immutable infrastructure patterns. Environments are created on-demand, populated with the exact required software stack, used for development and testing, and automatically destroyed when idle. This ensures zero drift, high security, and minimal cost footprint.

### Cost Optimization Benefits
- **70%+ Infrastructure Cost Reduction**: By running resources only during working hours (e.g., 9:00 AM to 6:00 PM on weekdays), compute costs decrease by up to ~73%.
- **Zero Idle Waste**: No unused EC2 instances or elasticity charges overnight or over weekends.
- **Automated Lifecycle**: Engineers focus on coding while automated GitHub workflows manage creation, verification, warning notifications, and destruction.

### DevOps Principles Applied
- **Infrastructure as Code (IaC)**: Standardized, reproducible AWS infrastructure declared in modular Terraform files.
- **Immutable Infrastructure**: Fresh environments are initialized cleanly via cloud-init without manual configuration drift.
- **GitOps & Continuous Delivery**: Workflows trigger automatically via GitHub Actions schedules or manual dispatches.
- **Shift-Left Security & Secrets Management**: AWS IAM security keys and webhooks are encrypted in GitHub Secrets; SSH private keys never leave local environments.
- **Observability & Feedback Loops**: Automated Slack notifications deliver real-time infrastructure lifecycle events directly to team channels.

---

# 2. Architecture Diagram

```mermaid
flowchart TD
    subgraph Local ["Developer Machine"]
        DEV["Developer"]
        KEY["Local Private Key\n(~/.ssh/ephemeral-dev-aws)"]
    end

    subgraph VersionControl ["Version Control & Automation"]
        GH_REPO["GitHub Repository"]
        GHA["GitHub Actions Workflows\n(Start / Warning / Destroy)"]
        SECRETS["GitHub Repository Secrets\n(AWS Keys & Slack Webhook)"]
    end

    subgraph RemoteState ["Remote State Storage"]
        S3["AWS S3 Remote Backend\n(Terraform State & Locks)"]
    end

    subgraph AWS ["AWS Cloud Infrastructure (VPC: 10.0.0.0/16)"]
        IGW["Internet Gateway"]
        RT["Public Route Table"]
        SG["Security Group\n(Ports 22, 80, 443, 5000)"]
        
        subgraph Subnet ["Public Subnet (10.0.1.0/24)"]
            subgraph Host ["EC2 Instance (Amazon Linux 2023)"]
                CLOUD_INIT["cloud-init Bootstrap Script"]
                DOCKER["Docker Engine"]
                KIND["kind Kubernetes Cluster"]
                
                subgraph K8S ["Kubernetes Workloads"]
                    FLASK_APP["Flask Application Pods"]
                    K8S_SVC["Kubernetes Service (NodePort/LoadBalancer)"]
                end
            end
        end
    end

    subgraph Messaging ["Notifications"]
        SLACK["Slack Channel\n(#ops-notifications)"]
    end

    DEV -->|1. Git Push / Manual Trigger| GH_REPO
    GH_REPO --> GHA
    SECRETS -->|Inject AWS Credentials| GHA
    GHA -->|2. Terraform Init / Apply| S3
    GHA -->|3. Provision Infrastructure| AWS
    IGW --- RT --- Subnet
    SG --> Host
    CLOUD_INIT -->|Installs| DOCKER
    DOCKER -->|Deploys| KIND
    KIND -->|Runs| K8S_SVC
    K8S_SVC --> FLASK_APP
    GHA -->|4. Push Notification| SLACK
    DEV -->|5. Direct SSH Debugging| Host
    DEV -->|6. HTTP / Web Verification| K8S_SVC
```

---

# 3. Features

| Feature | Description |
| :--- | :--- |
| **Infrastructure as Code (IaC)** | Fully automated AWS infrastructure deployment using modular Terraform HCL scripts. |
| **Automated Provisioning** | Cloud-init shell bootstrapping automatically installs Docker, kind, kubectl, and deploys application services on boot. |
| **Self-Destruct Lifecycle** | Scheduled GitHub Actions workflows trigger automated tear-downs at end-of-day to avoid overnight billing. |
| **Security Controls** | Ingress filtering with tightly constrained Security Groups, Key Pair SSH access, and secure secret injection. |
| **Remote State Management** | Centralized Terraform state stored securely in an AWS S3 bucket with state locking support. |
| **Containerized Application** | Python Flask application packaged inside optimized Docker containers. |
| **Kubernetes Deployment** | Local Kubernetes cluster running via `kind` inside EC2, exposing services through standard Kubernetes Service objects. |
| **Scheduled Automation** | Cron-based GitHub Actions workflows to spin up environments every morning and destroy them every evening. |
| **Real-time Notifications** | Rich Slack notifications dispatched on environment provisioning, pre-destruction warnings, and cleanup completion. |
| **Cost Optimization** | Reduces continuous compute costs by up to 73% by enforcing ephemeral operational schedules. |

---

# 4. Repository Structure

```
.
├── .github
│   └── workflows
│       ├── environment-destroy.yml    # Automated end-of-day tear-down workflow
│       ├── environment-manual.yml     # Manual dispatch workflow for ad-hoc environments
│       ├── environment-start.yml       # Morning automated provisioning workflow
│       └── environment-warning.yml     # Pre-destruction alert workflow
├── app
│   ├── app.py                         # Production-grade Python Flask web server
│   ├── Dockerfile                     # Container image definition for Flask app
│   └── requirements.txt               # Application Python dependencies
├── keys
│   └── example-dev-environment.pub.example # Public SSH key reference schema
├── kubernetes
│   ├── deployment.yaml                # Kubernetes Deployment spec for Flask app
│   ├── kind-config.yaml               # kind cluster configuration with port mappings
│   ├── namespace.yaml                 # Dedicated Kubernetes namespace definition
│   └── service.yaml                   # Kubernetes Service exposing Flask app
├── scripts
│   ├── bootstrap.sh                   # EC2 cloud-init provisioning & cluster deployment
│   ├── check-activity.sh              # Safety script verifying active developer sessions
│   ├── destroy-guard.sh               # Prevention guard ensuring safe environment teardown
│   └── wait-for-application.sh        # Healthcheck polling script for app readiness
├── terraform
│   └── aws
│       ├── bootstrap                  # S3 Remote State Backend initial infrastructure
│       └── environment                # Core AWS ephemeral environment HCL definitions
└── README.md                          # Platform documentation
```

### Directory Roles & Responsibilities
- `.github/workflows/`: CI/CD automation pipelines managing morning startup, warning alerts, manual dispatches, and evening shutdowns.
- `app/`: Source code, dependency manifests, and containerization instructions for the web application.
- `keys/`: Placeholders and instructions for managing public SSH keys securely.
- `kubernetes/`: Manifest files declaring Kubernetes namespaces, deployments, services, and `kind` cluster runtime specs.
- `scripts/`: Shell automation powering cloud-init instance setup, safety verification, healthchecks, and teardown guards.
- `terraform/aws/`: Declarative Infrastructure as Code divided into backend initialization (`bootstrap`) and environment provisioners (`environment`).

---

# 5. Prerequisites

Before deploying the platform, ensure the following CLI tools and accounts are installed and configured on your machine:

| Tool | Recommended Version | Installation Command (Linux / macOS) |
| :--- | :--- | :--- |
| **AWS Account & CLI** | `v2.x` | `curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && unzip awscliv2.zip && sudo ./aws/install` |
| **Terraform** | `>= 1.5.0` | `sudo apt-get update && sudo apt-get install -y terraform` or `brew install terraform` |
| **Git** | `>= 2.30` | `sudo apt install git -y` or `brew install git` |
| **Docker Engine** | `>= 24.0` | `curl -fsSL https://get.docker.com \| sh` |
| **OpenSSH Client** | standard | `sudo apt install openssh-client -y` |
| **GitHub Account** | N/A | Active GitHub account with repository admin privileges to configure Secrets. |

---

# 6. Complete Deployment Guide From Scratch

Follow this step-by-step guide to deploy the platform from a clean machine:

### Step 1: Clone Repository
Clone the platform codebase to your workstation:
```bash
git clone https://github.com/your-username/Ephemeral_Dev_Environment_Automation_Platform.git
cd Ephemeral_Dev_Environment_Automation_Platform
```

### Step 2: Install Application Requirements
Verify local application dependencies for testing:
```bash
cd app
pip install -r requirements.txt
cd ..
```

### Step 3: Configure AWS Credentials
Configure your AWS CLI with an IAM user possessing permissions for VPC, EC2, S3, and IAM management:
```bash
aws configure
```
Input your credentials when prompted:
- **AWS Access Key ID**: `YOUR_AWS_ACCESS_KEY_ID`
- **AWS Secret Access Key**: `YOUR_AWS_SECRET_ACCESS_KEY`
- **Default region name**: `us-east-1` (or your target region)
- **Default output format**: `json`

### Step 4: Verify AWS Authentication
Verify that your AWS credentials are authenticated:
```bash
aws sts get-caller-identity
```
*Expected Output:*
```json
{
    "UserId": "AIDAXXXXXXXXXXXXXXXXX",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/devops-admin"
}
```

---

# 7. SSH Key Management (Very Important)

The EC2 development instance uses SSH key authentication for secure administrative access.

A public SSH key is provided to AWS during Terraform deployment, while the private key remains exclusively on the local machine.

### Key Paths Specification
- **Public Key Path (uploaded to AWS)**: `~/.ssh/ephemeral-dev-aws.pub`
- **Private Key Path (never uploaded)**: `~/.ssh/ephemeral-dev-aws`

### Step 1: Generate Key Pair
Generate a high-security `ed25519` key pair locally:
```bash
ssh-keygen \
  -t ed25519 \
  -f ~/.ssh/ephemeral-dev-aws \
  -C "ephemeral-dev"
```
When prompted for a passphrase, press Enter for empty or specify a passphrase.

### Step 2: Set Strict File Permissions
Set standard UNIX file permissions to protect your private key:
```bash
chmod 600 ~/.ssh/ephemeral-dev-aws
chmod 644 ~/.ssh/ephemeral-dev-aws.pub
```

### Step 3: Verify Local SSH Keys
Ensure both private and public key files exist:
```bash
ls -la ~/.ssh/ephemeral-dev-aws*
```
*Expected Output:*
```text
-rw------- 1 user group 419 Aug 5 00:00 /home/user/.ssh/ephemeral-dev-aws
-rw-r--r-- 1 user group 104 Aug 5 00:00 /home/user/.ssh/ephemeral-dev-aws.pub
```

### Step 4: Terraform Configuration Integration
Terraform references the public key file in `terraform/aws/environment/variables.tf` or `terraform.tfvars`:
```hcl
ssh_public_key_path = "~/.ssh/ephemeral-dev-aws.pub"
```

### Step 5: Connecting to the Provisioned EC2 Instance
Connect securely to your ephemeral EC2 host once Terraform outputs the `ec2_public_ip`:
```bash
ssh -i ~/.ssh/ephemeral-dev-aws ec2-user@<PUBLIC_IP>
```

---

# 8. Terraform Deployment

Navigate to the environment Terraform directory:
```bash
cd terraform/aws/environment
```

### Execution Workflow & Commands

1. **Initialize Terraform & Backend**:
   Downloads AWS provider plugins and initializes the S3 backend state module.
   ```bash
   terraform init
   ```

2. **Validate Syntax & HCL Structure**:
   Ensures syntax correctness across all `.tf` files.
   ```bash
   terraform validate
   ```

3. **Generate Execution Plan**:
   Previews all AWS resources that will be created without applying changes.
   ```bash
   terraform plan
   ```

4. **Apply Infrastructure Provisioning**:
   Executes the build plan and provisions infrastructure in AWS.
   ```bash
   terraform apply -auto-approve
   ```

### Provisioned Resources List
- **AWS VPC**: Dedicated Virtual Private Cloud isolated with IP CIDR `10.0.0.0/16`.
- **AWS Public Subnet**: Subnet `10.0.1.0/24` with auto-assign public IPv4 enabled.
- **AWS Internet Gateway**: Attaches to VPC to route inbound/outbound internet traffic.
- **AWS Route Table**: Maps `0.0.0.0/0` destination traffic directly to the Internet Gateway.
- **AWS Security Group**: Filters traffic, allowing inbound ports `22` (SSH), `80` (HTTP), `443` (HTTPS), and `5000` (Flask Service).
- **AWS Key Pair**: Registers your local `~/.ssh/ephemeral-dev-aws.pub` public key in AWS.
- **AWS EC2 Instance**: Launches an `t3.medium` Amazon Linux 2023 instance equipped with `cloud-init`.

> [!TIP]
> **Instance Sizing Flexibility**: The default configuration provisions a `t3.medium` instance ideal for lightweight dev and testing. For compute-heavy or multi-service microservice workloads, override `instance_type` in `terraform/aws/environment/terraform.tfvars` (e.g., `instance_type = "t3.large"` or `"c6i.xlarge"`).

---

# 9. GitHub Actions Setup

The platform features automated workflow lifecycle management configured in `.github/workflows/`:

```
.github/workflows/
├── environment-destroy.yml
├── environment-manual.yml
├── environment-start.yml
└── environment-warning.yml
```

### 1. `environment-start.yml` (Morning Startup)
- **Trigger**: Cron schedule (e.g. `0 7 * * 1-5` - 7:00 AM UTC Mon-Fri) or manual `workflow_dispatch`.
- **Execution Workflow**:
  1. Checks out repository code.
  2. Sets up Terraform CLI.
  3. Authenticates with AWS using Repository Secrets.
  4. Runs `terraform init` and `terraform apply -auto-approve`.
  5. Obtains EC2 Public IP, verifies bootstrap completion, and executes automated end-to-end integration tests (`scripts/wait-for-application.sh`).
  6. Dispatches a Slack notification confirming the environment is active with connection URL.

### 2. `environment-warning.yml` (Pre-Destruction Warning)
- **Trigger**: Cron schedule (e.g. `45 18 * * 1-5` - 6:45 PM UTC Mon-Fri) or manual `workflow_dispatch`.
- **Execution Workflow**:
  1. Executes pre-destruction checks.
  2. Sends a Slack warning notification alerting developers that the environment will self-destruct in 15 minutes.

### 3. `environment-destroy.yml` (Evening Teardown)
- **Trigger**: Cron schedule (e.g. `0 19 * * 1-5` - 7:00 PM UTC Mon-Fri) or manual `workflow_dispatch`.
- **Execution Workflow**:
  1. Runs `scripts/destroy-guard.sh` to check for active SSH developer sessions or active lock overrides.
  2. Executes `terraform destroy -auto-approve` inside `terraform/aws/environment`.
  3. Cleans up temporary dynamic state markers.
  4. Dispatches a Slack notification confirming complete infrastructure termination and zero-cost state achieved.

---

# 10. GitHub Secrets Configuration

To enable automated provisioning via GitHub Actions, AWS access keys and Slack webhook endpoints must be configured in GitHub Secrets.

### Steps to Add Secrets
1. Open your repository on GitHub.
2. Navigate to: **Settings** $\rightarrow$ **Secrets and variables** $\rightarrow$ **Actions**.
3. Click **New repository secret** for each required key:

| Secret Name | Description | Example / Format |
| :--- | :--- | :--- |
| `AWS_ACCESS_KEY_ID` | AWS IAM User Access Key ID | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM User Secret Access Key | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| `SLACK_WEBHOOK_URL` | Incoming Webhook URL from Slack | `https://hooks.slack.com/services/T00/B00/X00` |

### Security Rationale
By storing credentials in GitHub Secrets, no sensitive access keys or private tokens are hardcoded into Git source files or committed to public branches.

---

# 11. Slack Notification Setup

Real-time notification hooks keep the team informed of ephemeral environment state changes.

### Step 1: Create Slack Incoming Webhook
1. Go to your Slack Workspace App Management page (`api.slack.com/apps`).
2. Create a new App named **Ephemeral Dev Bot** and install it to your target workspace.
3. Enable **Incoming Webhooks** and click **Add New Webhook to Workspace**.
4. Select your notification channel (e.g., `#devops-alerts`) and copy the generated Webhook URL.
5. Save the Webhook URL into GitHub Secrets as `SLACK_WEBHOOK_URL`.

### Automated Slack Event Lifecycle Messages
- **Environment Started**: `🚀 Ephemeral Dev Environment is LIVE! Public IP: 54.210.X.X | App URL: http://54.210.X.X`
- **Environment Warning**: `⚠️ WARNING: Ephemeral Dev Environment will self-destruct in 15 minutes!`
- **Environment Destroyed**: `🛑 Ephemeral Dev Environment destroyed successfully. AWS resources released.`
- **Workflow Failure**: `❌ ALERT: Ephemeral Environment workflow failed. Check GitHub Actions logs.`

---

# 12. Kubernetes Deployment

The EC2 instance automatically installs `kind` (Kubernetes in Docker) and `kubectl` during initial boot via `scripts/bootstrap.sh`.

### Provisioning Flow
1. `cloud-init` runs `bootstrap.sh`.
2. `kind` initializes a single-node Kubernetes cluster using `/kubernetes/kind-config.yaml`.
3. `kubectl` applies Kubernetes manifests:
   ```bash
   kubectl apply -f kubernetes/namespace.yaml
   kubectl apply -f kubernetes/deployment.yaml
   kubectl apply -f kubernetes/service.yaml
   ```

### Operational Commands (Inside EC2 Host)
Once connected via SSH (`ssh -i ~/.ssh/ephemeral-dev-aws ec2-user@PUBLIC_IP`), verify Kubernetes cluster status:

```bash
# Check kind cluster list
kind get clusters

# Verify node readiness
kubectl get nodes

# Inspect running pods across all namespaces
kubectl get pods -A

# Inspect deployed application service
kubectl get services -n ephemeral-dev
```

---

# 13. Application Verification

Verify that your Flask application container and Kubernetes service are functioning properly:

### 1. Verify Container Runtime (Docker)
Connect via SSH and check running containers:
```bash
docker ps
```
*Output confirms `kind-control-plane` container is active and handling cluster workloads.*

### 2. Verify Kubernetes Resources
```bash
kubectl get pods -n ephemeral-dev -o wide
```
*Expected Output:*
```text
NAME                                 READY   STATUS    RESTARTS   AGE   IP           NODE
flask-app-deployment-6d88478-x9z2p   1/1     Running   0          2m    10.240.0.4   kind-control-plane
```

### 3. Verify HTTP Response via Terminal
Execute `curl` against the instance public IP or localhost:
```bash
curl -I http://localhost:5000
```
*Expected Output:*
```http
HTTP/1.1 200 OK
Content-Type: application/json
Date: Wed, 05 Aug 2026 00:00:00 GMT
```

### 4. Verify Browser Access
Open your web browser and navigate to:
```text
http://<EC2_PUBLIC_IP>
```
You will see the live Ephemeral Dev Environment dashboard rendering health checks, uptime stats, and platform metadata.

---

# 14. Lifecycle Explanation

```
 07:00 AM UTC                        06:45 PM UTC        07:00 PM UTC
     │                                    │                   │
     ▼                                    ▼                   ▼
┌─────────┐   ┌───────────┐   ┌───────┐  ┌─────────┐   ┌────────────┐   ┌───────────┐
│ Morning │──>│ Terraform │──>│ EC2   │─>│ Warning │──>│  Safety    │──>│ Terraform │
│ Trigger │   │  Apply    │   │ Boot  │  │ Alert   │   │ Guard Check│   │ Destroy   │
└─────────┘   └───────────┘   └───────┘  └─────────┘   └────────────┘   └───────────┘
                                  │                                           │
                                  ▼                                           ▼
                             ┌─────────┐                                 ┌───────────┐
                             │ Docker  │                                 │ Zero AWS  │
                             │ + kind  │                                 │ Compute   │
                             │ App Live│                                 │ Cost      │
                             └─────────┘                                 └───────────┘
```

### Morning Phase (07:00 AM)
1. **GitHub Actions Trigger**: Scheduled CRON fires `environment-start.yml`.
2. **IaC Provisioning**: Terraform provisions VPC, Subnet, Security Groups, Key Pair, and EC2.
3. **Automated Bootstrapping**: `cloud-init` launches `bootstrap.sh`, installing Docker, kind, and deploying Kubernetes manifests.
4. **Notification**: Slack bot broadcasts active IP link to engineers.

### Working Hours Phase (07:00 AM - 06:45 PM)
- Developers log in via SSH or access the HTTP service endpoints.
- Code changes and integration testing run in isolated containerized environments.

### Evening Phase (06:45 PM - 07:00 PM)
1. **Pre-Destruction Alert (06:45 PM)**: `environment-warning.yml` sends Slack alert warning of shutdown.
2. **Safety Evaluation (07:00 PM)**: `environment-destroy.yml` checks for manual override locks or active SSH sessions using `scripts/destroy-guard.sh`.
3. **Automated Teardown**: `terraform destroy -auto-approve` removes all provisioned AWS cloud infrastructure.
4. **Final Notification**: Slack bot confirms shutdown; cloud billing returns to $0.00/hr.

---

# 15. Security Practices

- **Zero Hardcoded Credentials**: AWS Access Keys and Webhooks are encrypted in GitHub Secrets.
- **Local Private Key Retention**: SSH private keys (`~/.ssh/ephemeral-dev-aws`) are strictly retained on local developer machines and never committed to repository branches or uploaded to cloud storage.
- **Strict Ingress Rules**: Security Groups limit inbound access specifically to necessary application and administrative ports.
- **Remote State Protection**: Terraform state is stored off-site in AWS S3 with bucket encryption and access logging enabled.
- **Resource Tagging Policy**: All AWS resources are tagged with `Environment = Ephemeral-Dev` and `ManagedBy = Terraform` for automated governance and cost auditing.

---

# 16. Cost Optimization

### Cost Analysis: 24/7 Persistent vs. Ephemeral Schedule

Assuming an `t3.medium` EC2 instance ($0.0416/hr) with attached 20GB EBS storage ($0.08/GB-month):

| Operational Strategy | Monthly Hours Active | Compute Cost (Approx) | Storage/Network Cost | Total Estimated Monthly Cost | Savings |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Traditional 24/7 Host** | 720 hours | ~$30.00 | ~$2.00 | **~$32.00 / month** | 0% (Baseline) |
| **Ephemeral Platform (10h/day, Mon-Fri)** | ~210 hours | ~$8.70 | ~$0.50 | **~$9.20 / month** | **~71.2% Reduction** |

By automatically destroying the infrastructure overnight and during weekends, cloud expenditure drops by **over 70%** per developer instance.

---

# 17. Troubleshooting Guide

| Issue | Root Cause | Resolution Command / Steps |
| :--- | :--- | :--- |
| **Terraform State Lock Error** | A previous operation crashed before releasing the S3 state lock. | Run `terraform force-unlock <LOCK-ID>` inside `terraform/aws/environment`. |
| **SSH Connection Timeout** | Security Group blocked port 22 or EC2 is still initializing. | Verify IP with `aws ec2 describe-instances` and test security group ingress rule. |
| **Wrong AWS Region Error** | AWS CLI or Terraform defaulted to an unauthorized region. | Export target region explicitly: `export AWS_DEFAULT_REGION=us-east-1`. |
| **Docker Permission Denied** | User not in the `docker` Linux group. | Execute `sudo usermod -aG docker ec2-user` and restart terminal session. |
| **Kubernetes Pod Failures** | Container image pull failure or resource constraint on kind host. | SSH to EC2, run `kubectl describe pod <pod-name> -n ephemeral-dev`, check `docker logs`. |
| **Missing SSH Key Error** | Terraform cannot find public key at specified local path. | Generate key with `ssh-keygen -t ed25519 -f ~/.ssh/ephemeral-dev-aws` before running `terraform apply`. |
| **AWS Credentials Errors** | Expired or incorrect AWS keys configured in environment or GitHub Secrets. | Re-verify credentials using `aws sts get-caller-identity`. |

### How to Force-Unlock a Stuck Terraform State
If a pipeline step terminates unexpectedly, Terraform may leave the state file locked in S3. To clear the lock:
1. Locate the `LOCK-ID` string in the error log output (e.g., `Lock Info: ID: 5a81e9b2-xxxx`).
2. Run the force-unlock command inside `terraform/aws/environment`:
   ```bash
   cd terraform/aws/environment
   terraform force-unlock <LOCK-ID>
   ```
3. Re-run `terraform plan` to confirm state access is restored.

---

# 18. Cleanup

### Manual Cleanup
To immediately tear down the infrastructure manually from your workstation:
```bash
cd terraform/aws/environment
terraform destroy -auto-approve
```

### Automated Cleanup
Trigger the automated teardown pipeline via GitHub Actions:
1. Go to your repository on GitHub.
2. Navigate to **Actions** $\rightarrow$ **Environment Destroy Workflow**.
3. Click **Run workflow** $\rightarrow$ **Branch: main** $\rightarrow$ **Run workflow**.

---

# 19. Final Professional Summary

The **Ephemeral Dev Environment Automation Platform** demonstrates an end-to-end production-grade implementation of modern DevOps engineering practices:

- **Infrastructure as Code**: Declarative cloud provisioning with Terraform and S3 backend management.
- **Cloud Automation**: Event-driven CI/CD lifecycle automation using GitHub Actions.
- **Container Orchestration**: Production-aligned Kubernetes container deployment using Docker and `kind`.
- **Cost Engineering**: Data-driven, automated resource scheduling resulting in over 70% cloud cost reduction.
- **DevOps Lifecycle Management**: Continuous monitoring, automated healthchecks, pre-destruction guardrails, and real-time Slack notifications.

This repository serves as a showcase of cloud-native architecture, infrastructure security, and automated lifecycle governance.
