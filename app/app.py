import logging
import math
import os
import signal
import socket
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Any

from flask import Flask, jsonify, render_template_string, request

# ---------------------------------------------------------------------------
# Structured logging
#
# Uses a plain-text format that is readable in both `docker logs` and
# `kubectl logs` without requiring a log-aggregation agent.
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
    stream=sys.stdout,   # stdout so Docker/K8s captures it correctly
)

logger = logging.getLogger("ephemeral-dev-app")


app = Flask(__name__)

APP_NAME = os.getenv(
    "APP_NAME",
    "Scheduled Self-Destructing Environment"
)

APP_VERSION = os.getenv(
    "APP_VERSION",
    "1.0.0"
)

ENVIRONMENT = os.getenv(
    "ENVIRONMENT",
    "development"
)

CLOUD_PROVIDER = os.getenv("CLOUD_PROVIDER", "AWS")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
CLUSTER_NAME = os.getenv("CLUSTER_NAME", "ephemeral-dev-cluster")
K8S_NAMESPACE = os.getenv("K8S_NAMESPACE", "ephemeral-dev")

START_TIME = time.time()

# ---------------------------------------------------------------------------
# Metrics counters (in-memory, thread-safe)
#
# Intentionally simple -- no Prometheus client needed.
# Resets on pod/container restart, which is fine for a DevOps demo.
# ---------------------------------------------------------------------------

_request_lock = threading.Lock()
_total_requests: int = 0


def _increment_requests() -> None:
    """Thread-safe request counter increment."""
    global _total_requests
    with _request_lock:
        _total_requests += 1


def _get_request_count() -> int:
    """Thread-safe request counter read."""
    with _request_lock:
        return _total_requests



# ---------------------------------------------------------------------------
# Environment variable validation
#
# Validates required configuration at startup and logs warnings for any
# variables that fall back to defaults.  No secrets are logged.
# ---------------------------------------------------------------------------

def _validate_env() -> None:
    """Log warnings for environment variables using default values."""
    defaults = {
        "APP_NAME": "Scheduled Self-Destructing Environment",
        "APP_VERSION": "1.0.0",
        "ENVIRONMENT": "development",
        "CLOUD_PROVIDER": "AWS",
        "AWS_REGION": "us-east-1",
        "CLUSTER_NAME": "ephemeral-dev-cluster",
        "K8S_NAMESPACE": "ephemeral-dev",
    }
    for var, default in defaults.items():
        if os.getenv(var) is None:
            logger.warning(
                "Environment variable %s not set; using default: %s",
                var,
                default,
            )


# ---------------------------------------------------------------------------
# In-memory platform state
#
# This mirrors what, in production, would live behind Terraform state, the
# Kubernetes API, and GitHub Actions -- kept in memory here so the whole
# platform is runnable as a single file with zero external dependencies.
# State resets whenever the process restarts, which is a reasonable stand-in
# for "the environment is offline until something provisions it again".
# ---------------------------------------------------------------------------

VALID_STATUSES = ("OFFLINE", "RUNNING", "WARNING", "DESTROYING")

environment_state: dict[str, Any] = {
    "status": "RUNNING",
    "environment": ENVIRONMENT,
    "version": APP_VERSION,
    "cloud": CLOUD_PROVIDER,
    "region": AWS_REGION,
    "started_at": time.time() - 9300,
}

lifecycle_events: list[dict[str, Any]] = []

workflow_runs: list[dict[str, Any]] = [
    {
        "workflow": "environment-start.yml",
        "status": "success",
        "branch": "main",
        "commit": "a3f9c1e",
        "triggeredBy": "octavia-dev",
        "createdAt": time.time() - 9300,
    },
    {
        "workflow": "environment-destroy.yml",
        "status": "success",
        "branch": "main",
        "commit": "b71de02",
        "triggeredBy": "scheduler",
        "createdAt": time.time() - 96000,
    },
    {
        "workflow": "environment-start.yml",
        "status": "success",
        "branch": "feature/gpu-nodes",
        "commit": "44c8aa1",
        "triggeredBy": "marcus-lee",
        "createdAt": time.time() - 182000,
    },
]


def log_event(stage: str, message: str, status: str = "info") -> None:
    lifecycle_events.insert(
        0,
        {"stage": stage, "message": message, "status": status, "createdAt": time.time()},
    )
    del lifecycle_events[20:]


log_event("provision", "Terraform apply completed: 6 resources created", "success")
log_event("bootstrap", "Docker, kubectl, and kind installed on EC2 host", "success")
log_event("deploy", "Kubernetes deployment aws-dev-env-app rolled out", "success")
log_event("operate", "Developer session active", "info")

# Run startup validation and log the application start.
_validate_env()
logger.info(
    "Application started | name=%s version=%s env=%s host=%s",
    APP_NAME,
    APP_VERSION,
    ENVIRONMENT,
    socket.gethostname(),
)


def format_uptime(seconds: float) -> str:
    total_seconds = int(seconds)

    days, remaining = divmod(total_seconds, 86400)
    hours, remaining = divmod(remaining, 3600)
    minutes, seconds = divmod(remaining, 60)

    if days > 0:
        return f"{days}d {hours}h"

    if hours > 0:
        return f"{hours}h {minutes}m"

    if minutes > 0:
        return f"{minutes}m {seconds}s"

    return f"{seconds}s"


def get_environment_info() -> dict[str, Any]:
    """Return structured application and infrastructure metadata.

    Exposed via GET /api/info.  Includes Python version so Kubernetes
    operators can confirm the exact runtime in use.
    """
    uptime_seconds = time.time() - START_TIME

    return {
        "application": {
            "name": APP_NAME,
            "version": APP_VERSION,
            "environment": ENVIRONMENT,
            "status": "healthy",
        },
        "runtime": {
            "hostname": socket.gethostname(),
            # Python version string -- useful for debugging container images
            "python_version": sys.version,
            "uptime_seconds": round(uptime_seconds, 2),
            "uptime": format_uptime(uptime_seconds),
        },
        "infrastructure": {
            "cloud_provider": "AWS",
            "compute": "EC2",
            "container_runtime": "Docker",
            "orchestrator": "Kubernetes",
            "cluster_type": "kind",
            "automation": "GitHub Actions",
            "infrastructure_as_code": "Terraform",
        },
        "schedule": {
            "startup": "08:00",
            "shutdown": "18:00",
            "working_days": [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
            ],
            "weekend_state": "offline",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Environment lifecycle (state machine)
# ---------------------------------------------------------------------------

def _environment_payload() -> dict[str, Any]:
    now = time.time()
    started_at = environment_state["started_at"]
    running = environment_state["status"] != "OFFLINE"
    uptime_seconds = int(now - started_at) if started_at and running else 0

    return {
        "status": environment_state["status"],
        "environment": environment_state["environment"],
        "version": environment_state["version"],
        "cloud": environment_state["cloud"],
        "region": environment_state["region"],
        "uptimeSeconds": max(uptime_seconds, 0),
        "updatedAt": now,
    }


def start_environment() -> dict[str, Any]:
    environment_state["status"] = "RUNNING"
    environment_state["started_at"] = time.time()
    log_event("provision", "Terraform apply triggered via GitHub Actions", "success")
    log_event("bootstrap", "Bootstrap script installing Docker, kubectl, kind", "success")
    log_event("deploy", "Kubernetes manifests applied to kind cluster", "success")
    return _environment_payload()


def destroy_environment() -> dict[str, Any]:
    log_event("destroy", "Shutdown warning sent to active developer session", "warning")
    log_event("destroy", "Terraform destroy initiated", "info")
    environment_state["status"] = "DESTROYING"
    result = _environment_payload()

    # Simulated as immediate for a responsive demo; in production this
    # transition happens asynchronously once Terraform reports completion.
    environment_state["status"] = "OFFLINE"
    environment_state["started_at"] = None
    log_event("destroy", "Infrastructure fully decommissioned", "success")
    return result


def restart_environment() -> dict[str, Any]:
    log_event("restart", "Restart requested by developer", "info")
    destroy_environment()
    return start_environment()


# ---------------------------------------------------------------------------
# Infrastructure topology
# ---------------------------------------------------------------------------

def get_infrastructure_status() -> dict[str, Any]:
    status = environment_state["status"]
    running = status in ("RUNNING", "WARNING")
    node_status = "running" if running else ("provisioning" if status == "DESTROYING" else "offline")

    nodes = [
        {
            "id": "aws-cloud",
            "label": "AWS Cloud",
            "type": "provider",
            "status": node_status,
            "description": "Root account boundary for all ephemeral resources.",
            "metadata": {"accountId": "482910xxxxx", "region": AWS_REGION},
        },
        {
            "id": "vpc",
            "label": "VPC",
            "type": "network",
            "status": node_status,
            "description": "Isolated virtual network created per environment.",
            "metadata": {"cidr": "10.20.0.0/16", "vpcId": "vpc-0a1b2c3d4e"},
        },
        {
            "id": "public-subnet",
            "label": "Public Subnet",
            "type": "network",
            "status": node_status,
            "description": "Hosts the EC2 dev host with a route to the internet gateway.",
            "metadata": {"cidr": "10.20.1.0/24", "az": f"{AWS_REGION}a"},
        },
        {
            "id": "ec2",
            "label": "EC2 Instance",
            "type": "compute",
            "status": node_status,
            "description": "Single host running Docker and a kind Kubernetes cluster.",
            "metadata": {
                "instanceId": "i-0f3a9c2b7e1d4f6a2",
                "instanceType": "t3.large",
                "privateIp": "10.20.1.42",
                "publicIp": "54.212.88.17" if running else "-",
            },
        },
        {
            "id": "docker",
            "label": "Docker",
            "type": "runtime",
            "status": node_status,
            "description": "Container runtime installed by the bootstrap script.",
            "metadata": {"version": "26.1.4"},
        },
        {
            "id": "kind",
            "label": "kind Kubernetes Cluster",
            "type": "orchestration",
            "status": node_status,
            "description": "Single-node Kubernetes-in-Docker cluster for the dev environment.",
            "metadata": {"cluster": CLUSTER_NAME, "k8sVersion": "v1.30.2"},
        },
        {
            "id": "namespace",
            "label": "Namespace",
            "type": "orchestration",
            "status": node_status,
            "description": "Logical namespace isolating the developer's workloads.",
            "metadata": {"namespace": K8S_NAMESPACE},
        },
        {
            "id": "deployment",
            "label": "Deployment",
            "type": "workload",
            "status": node_status,
            "description": "Manages the replica set for the application pods.",
            "metadata": {"deployment": "aws-dev-env-app", "replicas": "1/1" if running else "0/0"},
        },
        {
            "id": "application",
            "label": "Application",
            "type": "workload",
            "status": "healthy" if running else "offline",
            "description": "The developer's application, reachable via NodePort.",
            "metadata": {"port": "30080"},
        },
    ]

    ids = [n["id"] for n in nodes]
    return {
        "environmentStatus": status,
        "nodes": nodes,
        "edges": [{"from": a, "to": b} for a, b in zip(ids, ids[1:])],
    }


# ---------------------------------------------------------------------------
# Kubernetes
# ---------------------------------------------------------------------------

def get_kubernetes_status() -> dict[str, Any]:
    status = environment_state["status"]
    running = status in ("RUNNING", "WARNING")
    payload = _environment_payload()

    pods = []
    if running:
        pods.append(
            {
                "name": "aws-dev-env-app-7d9f6c8b7-x2j4k",
                "status": "Running",
                "restarts": 0,
                "age": format_uptime(payload["uptimeSeconds"]),
                "ip": "10.244.0.10",
            }
        )

    return {
        "cluster": CLUSTER_NAME,
        "namespace": K8S_NAMESPACE,
        "node": {
            "name": "ephemeral-dev-cluster-control-plane",
            "status": "Ready" if running else "NotReady",
            "role": "control-plane",
            "kubeletVersion": "v1.30.2",
        },
        "deployment": {
            "name": "aws-dev-env-app",
            "desiredReplicas": 1 if running else 0,
            "availableReplicas": 1 if running else 0,
            "strategy": "RollingUpdate",
        },
        "service": {
            "name": "aws-dev-env-app-service",
            "type": "NodePort",
            "clusterIp": "10.96.145.201" if running else "-",
            "port": 80,
            "nodePort": 30080,
        },
        "pods": pods,
    }


# ---------------------------------------------------------------------------
# Cost optimization
# ---------------------------------------------------------------------------

HOURLY_RATE_USD = 0.0928  # t3.large on-demand, us-east-1
WORKING_HOURS_PER_DAY = 9
WORKING_DAYS_PER_MONTH = 22
HOURS_PER_MONTH = 24 * 30
MONTHS_LABELS = ["Feb", "Mar", "Apr", "May", "Jun", "Jul"]


def get_cost_status() -> dict[str, Any]:
    always_on_hours = HOURS_PER_MONTH
    ephemeral_hours = WORKING_HOURS_PER_DAY * WORKING_DAYS_PER_MONTH

    always_on_cost = round(always_on_hours * HOURLY_RATE_USD, 2)
    ephemeral_cost = round(ephemeral_hours * HOURLY_RATE_USD, 2)
    saved_hours = always_on_hours - ephemeral_hours
    savings_pct = round((1 - ephemeral_cost / always_on_cost) * 100)

    monthly_comparison = [
        {
            "month": month,
            "traditional": round(always_on_cost * (0.96 + 0.02 * i), 2),
            "ephemeral": round(ephemeral_cost * (0.94 + 0.03 * i), 2),
        }
        for i, month in enumerate(MONTHS_LABELS)
    ]

    return {
        "traditional": {
            "model": "Running 24/7",
            "hoursPerMonth": always_on_hours,
            "estimatedMonthlyCost": always_on_cost,
        },
        "ephemeral": {
            "model": "Running only working hours",
            "hoursPerMonth": ephemeral_hours,
            "estimatedMonthlyCost": ephemeral_cost,
        },
        "savingsPercent": savings_pct,
        "savedHoursPerMonth": saved_hours,
        "monthlyComparison": monthly_comparison,
        "instanceType": "t3.large",
        "hourlyRateUsd": HOURLY_RATE_USD,
    }


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

def get_security_status() -> dict[str, Any]:
    checks = [
        {
            "id": "ssh-restricted",
            "label": "SSH restricted",
            "status": "PASS",
            "detail": "Security group allows SSH only from the office and VPN CIDR ranges.",
        },
        {
            "id": "no-secrets-committed",
            "label": "No secrets committed",
            "status": "PASS",
            "detail": "gitleaks pre-commit hook and CI scan found no committed credentials.",
        },
        {
            "id": "terraform-remote-backend",
            "label": "Terraform remote backend",
            "status": "PASS",
            "detail": "State stored in an encrypted S3 bucket with DynamoDB state locking.",
        },
        {
            "id": "security-groups-configured",
            "label": "Security groups configured",
            "status": "PASS",
            "detail": "Ingress limited to required ports; all egress logged via VPC Flow Logs.",
        },
        {
            "id": "iam-permissions",
            "label": "IAM permissions",
            "status": "PASS",
            "detail": "Least-privilege role scoped to the ephemeral-platform resource tags only.",
        },
        {
            "id": "oidc-authentication",
            "label": "OIDC authentication",
            "status": "PASS",
            "detail": "GitHub Actions assumes an AWS role via OIDC -- no long-lived AWS keys stored.",
        },
    ]
    passing = sum(1 for c in checks if c["status"] == "PASS")
    return {"checks": checks, "passing": passing, "total": len(checks)}


# ---------------------------------------------------------------------------
# CI/CD automation
# ---------------------------------------------------------------------------

START_STEPS = [
    "GitHub Actions",
    "Terraform Init",
    "Terraform Plan",
    "Terraform Apply",
    "Bootstrap EC2",
    "Deploy Kubernetes",
]

DESTROY_STEPS = ["Shutdown Warning", "Validation", "Terraform Destroy"]


def get_cicd_status() -> dict[str, Any]:
    runs = sorted(workflow_runs, key=lambda r: r["createdAt"], reverse=True)[:10]
    return {
        "startWorkflow": {"name": "environment-start.yml", "steps": START_STEPS},
        "destroyWorkflow": {"name": "environment-destroy.yml", "steps": DESTROY_STEPS},
        "latestRun": runs[0] if runs else None,
        "recentRuns": runs,
    }


# ---------------------------------------------------------------------------
# Application monitoring
# ---------------------------------------------------------------------------

def get_monitoring_status() -> dict[str, Any]:
    status = environment_state["status"]
    running = status in ("RUNNING", "WARNING")
    payload = _environment_payload()
    elapsed = time.time() - START_TIME

    cpu = 18 + 12 * (0.5 + 0.5 * math.sin(elapsed / 37)) if running else 0
    memory = 34 + 9 * (0.5 + 0.5 * math.sin(elapsed / 53 + 1.2)) if running else 0
    rps = 6 + 4 * (0.5 + 0.5 * math.sin(elapsed / 29 + 0.4)) if running else 0
    p95 = 82 + 30 * (0.5 + 0.5 * math.sin(elapsed / 41 + 2.1)) if running else 0

    history = []
    for i in range(20):
        t = elapsed - (19 - i) * 15
        history.append(
            {
                "t": i,
                "cpu": round(max(0, 18 + 12 * (0.5 + 0.5 * math.sin(t / 37))), 1) if running else 0,
                "memory": round(max(0, 34 + 9 * (0.5 + 0.5 * math.sin(t / 53 + 1.2))), 1) if running else 0,
            }
        )

    return {
        "application": "aws-dev-env-app",
        "health": "Healthy" if running else "Offline",
        "metrics": {
            "cpuPercent": round(cpu, 1),
            "memoryPercent": round(memory, 1),
            "requestsPerSecond": round(rps, 1),
            "p95ResponseTimeMs": round(p95),
            "uptimeSeconds": payload["uptimeSeconds"],
        },
        "history": history,
    }


DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>{{ app_name }}</title>

    <style>
        :root {
            --background: #07111f;
            --surface: rgba(15, 29, 48, 0.82);
            --surface-light: rgba(30, 48, 72, 0.72);
            --border: rgba(148, 163, 184, 0.18);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --success: #34d399;
            --warning: #fbbf24;
            --accent: #38bdf8;
            --accent-secondary: #818cf8;
            --danger: #fb7185;
            --shadow: 0 20px 60px rgba(0, 0, 0, 0.35);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            min-height: 100vh;
            font-family:
                Inter,
                ui-sans-serif,
                system-ui,
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                sans-serif;
            color: var(--text-primary);
            background:
                radial-gradient(
                    circle at top left,
                    rgba(56, 189, 248, 0.16),
                    transparent 34%
                ),
                radial-gradient(
                    circle at top right,
                    rgba(129, 140, 248, 0.14),
                    transparent 30%
                ),
                linear-gradient(145deg, #020617, var(--background));
            overflow-x: hidden;
        }

        .grid-background {
            position: fixed;
            inset: 0;
            pointer-events: none;
            opacity: 0.16;
            background-image:
                linear-gradient(
                    rgba(148, 163, 184, 0.14) 1px,
                    transparent 1px
                ),
                linear-gradient(
                    90deg,
                    rgba(148, 163, 184, 0.14) 1px,
                    transparent 1px
                );
            background-size: 44px 44px;
            mask-image: linear-gradient(
                to bottom,
                black,
                transparent 88%
            );
        }

        .container {
            width: min(1180px, 92%);
            margin: 0 auto;
            padding: 42px 0 52px;
            position: relative;
            z-index: 1;
        }

        .topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 20px;
            margin-bottom: 42px;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 14px;
        }

        .brand-icon {
            width: 48px;
            height: 48px;
            display: grid;
            place-items: center;
            border-radius: 14px;
            background:
                linear-gradient(
                    135deg,
                    rgba(56, 189, 248, 0.24),
                    rgba(129, 140, 248, 0.28)
                );
            border: 1px solid var(--border);
            box-shadow: var(--shadow);
            font-size: 23px;
        }

        .brand h1 {
            font-size: 17px;
            letter-spacing: 0.02em;
        }

        .brand p {
            color: var(--text-secondary);
            font-size: 13px;
            margin-top: 3px;
        }

        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 9px;
            padding: 10px 15px;
            border-radius: 999px;
            border: 1px solid rgba(52, 211, 153, 0.2);
            background: rgba(52, 211, 153, 0.08);
            color: #a7f3d0;
            font-size: 13px;
            font-weight: 700;
        }

        .status-pill.warn {
            border-color: rgba(251, 191, 36, 0.3);
            background: rgba(251, 191, 36, 0.1);
            color: #fde68a;
        }

        .status-pill.destroy {
            border-color: rgba(251, 113, 133, 0.3);
            background: rgba(251, 113, 133, 0.1);
            color: #fecdd3;
        }

        .status-pill.off {
            border-color: rgba(148, 163, 184, 0.25);
            background: rgba(148, 163, 184, 0.08);
            color: #cbd5e1;
        }

        .status-dot {
            width: 9px;
            height: 9px;
            border-radius: 50%;
            background: var(--success);
            box-shadow: 0 0 16px var(--success);
            animation: pulse 1.9s infinite;
        }

        .status-pill.warn .status-dot {
            background: var(--warning);
            box-shadow: 0 0 16px var(--warning);
        }

        .status-pill.destroy .status-dot {
            background: var(--danger);
            box-shadow: 0 0 16px var(--danger);
        }

        .status-pill.off .status-dot {
            background: #94a3b8;
            box-shadow: none;
            animation: none;
        }

        @keyframes pulse {
            0%, 100% {
                opacity: 1;
                transform: scale(1);
            }

            50% {
                opacity: 0.45;
                transform: scale(0.75);
            }
        }

        .hero {
            display: grid;
            grid-template-columns: 1.35fr 0.65fr;
            gap: 24px;
            margin-bottom: 24px;
        }

        .panel {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 24px;
            box-shadow: var(--shadow);
            backdrop-filter: blur(18px);
        }

        .hero-main {
            padding: 40px;
            position: relative;
            overflow: hidden;
        }

        .hero-main::after {
            content: "";
            position: absolute;
            width: 260px;
            height: 260px;
            right: -90px;
            bottom: -120px;
            background: radial-gradient(
                circle,
                rgba(56, 189, 248, 0.22),
                transparent 67%
            );
        }

        .eyebrow {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            color: var(--accent);
            font-size: 12px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.14em;
            margin-bottom: 18px;
        }

        .hero-main h2 {
            max-width: 760px;
            font-size: clamp(34px, 5vw, 62px);
            line-height: 1.02;
            letter-spacing: -0.05em;
            margin-bottom: 20px;
        }

        .gradient-text {
            background:
                linear-gradient(
                    90deg,
                    #7dd3fc,
                    #a5b4fc,
                    #67e8f9
                );
            -webkit-background-clip: text;
            color: transparent;
        }

        .hero-description {
            max-width: 720px;
            color: var(--text-secondary);
            font-size: 16px;
            line-height: 1.75;
            margin-bottom: 30px;
        }

        .hero-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }

        .tag {
            padding: 9px 12px;
            border-radius: 10px;
            background: rgba(148, 163, 184, 0.08);
            border: 1px solid var(--border);
            color: #cbd5e1;
            font-size: 12px;
            font-weight: 700;
        }

        .environment-card {
            padding: 28px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-height: 100%;
        }

        .environment-card h3 {
            font-size: 15px;
            color: var(--text-secondary);
            margin-bottom: 20px;
        }

        .environment-name {
            font-size: 26px;
            font-weight: 800;
            margin-bottom: 6px;
            text-transform: capitalize;
        }

        .environment-subtitle {
            color: var(--text-secondary);
            font-size: 13px;
        }

        .schedule {
            margin-top: 34px;
            padding-top: 24px;
            border-top: 1px solid var(--border);
        }

        .schedule-row {
            display: flex;
            justify-content: space-between;
            gap: 18px;
            padding: 12px 0;
            font-size: 13px;
        }

        .schedule-row span:first-child {
            color: var(--text-secondary);
        }

        .schedule-row strong {
            color: var(--text-primary);
        }

        .cards {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 18px;
            margin-bottom: 24px;
        }

        .metric-card {
            padding: 24px;
        }

        .metric-label {
            color: var(--text-secondary);
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.09em;
            margin-bottom: 14px;
        }

        .metric-value {
            font-size: 26px;
            font-weight: 800;
            margin-bottom: 8px;
        }

        .metric-description {
            color: var(--text-secondary);
            font-size: 12px;
            line-height: 1.5;
        }

        .lower-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }

        .section {
            padding: 30px;
        }

        .section-title {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 14px;
            margin-bottom: 24px;
        }

        .section-title h3 {
            font-size: 18px;
        }

        .section-title span {
            color: var(--text-secondary);
            font-size: 12px;
        }

        .service-list {
            display: grid;
            gap: 13px;
        }

        .service {
            padding: 15px 16px;
            border: 1px solid var(--border);
            background: var(--surface-light);
            border-radius: 15px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 15px;
        }

        .service-info {
            display: flex;
            align-items: center;
            gap: 13px;
        }

        .service-icon {
            width: 39px;
            height: 39px;
            border-radius: 11px;
            display: grid;
            place-items: center;
            background: rgba(56, 189, 248, 0.1);
            border: 1px solid var(--border);
        }

        .service-name {
            font-size: 14px;
            font-weight: 800;
        }

        .service-description {
            color: var(--text-secondary);
            font-size: 11px;
            margin-top: 4px;
        }

        .service-status {
            color: #86efac;
            font-size: 11px;
            font-weight: 800;
        }

        .timeline {
            display: grid;
            gap: 18px;
        }

        .timeline-item {
            display: grid;
            grid-template-columns: 40px 1fr;
            gap: 14px;
            position: relative;
        }

        .timeline-item:not(:last-child)::after {
            content: "";
            position: absolute;
            left: 19px;
            top: 42px;
            width: 1px;
            height: calc(100% + 5px);
            background: var(--border);
        }

        .timeline-number {
            width: 40px;
            height: 40px;
            display: grid;
            place-items: center;
            border-radius: 50%;
            background: rgba(129, 140, 248, 0.14);
            border: 1px solid rgba(129, 140, 248, 0.28);
            color: #c7d2fe;
            font-weight: 800;
            font-size: 13px;
        }

        .timeline-content {
            padding-top: 3px;
        }

        .timeline-content h4 {
            font-size: 14px;
            margin-bottom: 5px;
        }

        .timeline-content p {
            color: var(--text-secondary);
            font-size: 12px;
            line-height: 1.6;
        }

        .events {
            display: grid;
            gap: 12px;
        }

        .event {
            display: grid;
            grid-template-columns: 10px 1fr;
            gap: 12px;
        }

        .event-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-top: 5px;
            background: var(--accent-secondary);
        }

        .event-dot.success { background: var(--success); }
        .event-dot.warning { background: var(--warning); }
        .event-dot.error { background: var(--danger); }

        .event-message {
            font-size: 13px;
        }

        .event-meta {
            color: var(--text-secondary);
            font-size: 11px;
            margin-top: 2px;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }

        footer {
            margin-top: 34px;
            color: var(--text-secondary);
            text-align: center;
            font-size: 12px;
        }

        .api-links {
            display: flex;
            justify-content: center;
            gap: 15px;
            flex-wrap: wrap;
            margin-top: 14px;
        }

        .api-links a {
            color: var(--accent);
            text-decoration: none;
            font-weight: 700;
        }

        .api-links a:hover {
            text-decoration: underline;
        }

        @media (max-width: 960px) {
            .hero,
            .lower-grid {
                grid-template-columns: 1fr;
            }

            .cards {
                grid-template-columns: repeat(2, 1fr);
            }
        }

        @media (max-width: 620px) {
            .container {
                width: min(94%, 1180px);
                padding-top: 24px;
            }

            .topbar {
                align-items: flex-start;
                flex-direction: column;
            }

            .hero-main {
                padding: 28px 24px;
            }

            .cards {
                grid-template-columns: 1fr;
            }

            .metric-card,
            .section,
            .environment-card {
                padding: 22px;
            }
        }
    </style>
</head>

<body>
    <div class="grid-background"></div>

    <main class="container">
        <header class="topbar">
            <div class="brand">
                <div class="brand-icon">⚡</div>

                <div>
                    <h1>{{ app_name }}</h1>
                    <p>Automated ephemeral infrastructure platform</p>
                </div>
            </div>

            <div class="status-pill {{ status_class }}">
                <span class="status-dot"></span>
                {{ status }}
            </div>
        </header>

        <section class="hero">
            <div class="panel hero-main">
                <div class="eyebrow">
                    Cloud Cost Optimization
                </div>

                <h2>
                    Infrastructure that exists
                    <span class="gradient-text">
                        only when needed.
                    </span>
                </h2>

                <p class="hero-description">
                    This environment is automatically provisioned during
                    working hours and safely destroyed after the workday,
                    reducing idle cloud costs while preserving a complete
                    Kubernetes-based development platform.
                </p>

                <div class="hero-tags">
                    <span class="tag">Terraform</span>
                    <span class="tag">AWS EC2</span>
                    <span class="tag">Docker</span>
                    <span class="tag">Kubernetes</span>
                    <span class="tag">kind</span>
                    <span class="tag">GitHub Actions</span>
                </div>
            </div>

            <div class="panel environment-card">
                <div>
                    <h3>Current environment</h3>

                    <div class="environment-name">
                        {{ environment }}
                    </div>

                    <div class="environment-subtitle">
                        Version {{ app_version }}
                    </div>
                </div>

                <div class="schedule">
                    <div class="schedule-row">
                        <span>Start schedule</span>
                        <strong>08:00 AM</strong>
                    </div>

                    <div class="schedule-row">
                        <span>Destroy schedule</span>
                        <strong>06:00 PM</strong>
                    </div>

                    <div class="schedule-row">
                        <span>Weekend state</span>
                        <strong>Offline</strong>
                    </div>
                </div>
            </div>
        </section>

        <section class="cards">
            <div class="panel metric-card">
                <div class="metric-label">Application status</div>
                <div class="metric-value">Healthy</div>
                <div class="metric-description">
                    Flask API is running and accepting requests.
                </div>
            </div>

            <div class="panel metric-card">
                <div class="metric-label">Hostname</div>
                <div class="metric-value">{{ hostname }}</div>
                <div class="metric-description">
                    Current container or Kubernetes pod hostname.
                </div>
            </div>

            <div class="panel metric-card">
                <div class="metric-label">Application uptime</div>
                <div class="metric-value">{{ uptime }}</div>
                <div class="metric-description">
                    Time elapsed since the application started.
                </div>
            </div>

            <div class="panel metric-card">
                <div class="metric-label">Estimated savings</div>
                <div class="metric-value">~{{ savings_percent }}%</div>
                <div class="metric-description">
                    Compared with running the instance continuously.
                </div>
            </div>
        </section>

        <section class="lower-grid">
            <div class="panel section">
                <div class="section-title">
                    <h3>Platform Components</h3>
                    <span>{{ status }}</span>
                </div>

                <div class="service-list">
                    <div class="service">
                        <div class="service-info">
                            <div class="service-icon">☁</div>

                            <div>
                                <div class="service-name">AWS EC2</div>
                                <div class="service-description">
                                    Ephemeral compute infrastructure
                                </div>
                            </div>
                        </div>

                        <div class="service-status">{{ component_status }}</div>
                    </div>

                    <div class="service">
                        <div class="service-info">
                            <div class="service-icon">🐳</div>

                            <div>
                                <div class="service-name">Docker</div>
                                <div class="service-description">
                                    Container runtime
                                </div>
                            </div>
                        </div>

                        <div class="service-status">{{ component_status }}</div>
                    </div>

                    <div class="service">
                        <div class="service-info">
                            <div class="service-icon">☸</div>

                            <div>
                                <div class="service-name">Kubernetes</div>
                                <div class="service-description">
                                    kind-based orchestration cluster
                                </div>
                            </div>
                        </div>

                        <div class="service-status">{{ component_status }}</div>
                    </div>

                    <div class="service">
                        <div class="service-info">
                            <div class="service-icon">⚙</div>

                            <div>
                                <div class="service-name">GitHub Actions</div>
                                <div class="service-description">
                                    Scheduled environment automation
                                </div>
                            </div>
                        </div>

                        <div class="service-status">ENABLED</div>
                    </div>
                </div>
            </div>

            <div class="panel section">
                <div class="section-title">
                    <h3>Environment Lifecycle</h3>
                    <span>Automated workflow</span>
                </div>

                <div class="timeline">
                    <div class="timeline-item">
                        <div class="timeline-number">1</div>

                        <div class="timeline-content">
                            <h4>Provision infrastructure</h4>
                            <p>
                                Terraform creates the EC2 instance,
                                networking, and security configuration.
                            </p>
                        </div>
                    </div>

                    <div class="timeline-item">
                        <div class="timeline-number">2</div>

                        <div class="timeline-content">
                            <h4>Build the platform</h4>
                            <p>
                                Docker and kind create a lightweight
                                Kubernetes cluster on the instance.
                            </p>
                        </div>
                    </div>

                    <div class="timeline-item">
                        <div class="timeline-number">3</div>

                        <div class="timeline-content">
                            <h4>Deploy the application</h4>
                            <p>
                                Kubernetes starts the Deployment and exposes
                                the application through a Service.
                            </p>
                        </div>
                    </div>

                    <div class="timeline-item">
                        <div class="timeline-number">4</div>

                        <div class="timeline-content">
                            <h4>Destroy safely</h4>
                            <p>
                                The pipeline warns the team, performs safety
                                checks, and destroys unused infrastructure.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <section class="lower-grid">
            <div class="panel section">
                <div class="section-title">
                    <h3>Recent Activity</h3>
                    <span>Live lifecycle events</span>
                </div>

                <div class="events">
                    {% for event in events %}
                    <div class="event">
                        <div class="event-dot {{ event.status }}"></div>
                        <div>
                            <div class="event-message">{{ event.message }}</div>
                            <div class="event-meta">{{ event.stage }}</div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>

            <div class="panel section">
                <div class="section-title">
                    <h3>Security Posture</h3>
                    <span>{{ security_passing }} / {{ security_total }} checks passing</span>
                </div>

                <div class="service-list">
                    {% for check in security_checks %}
                    <div class="service">
                        <div class="service-info">
                            <div class="service-icon">🔒</div>
                            <div>
                                <div class="service-name">{{ check.label }}</div>
                                <div class="service-description">{{ check.detail }}</div>
                            </div>
                        </div>
                        <div class="service-status">{{ check.status }}</div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </section>

        <footer>
            Generated at {{ current_time }} UTC
            · {{ app_name }} v{{ app_version }}

            <div class="api-links">
                <a href="/health">Health API</a>
                <a href="/ready">Readiness API</a>
                <a href="/api/info">Environment Info</a>
                <a href="/api/environment/status">Environment Status</a>
                <a href="/api/infrastructure/status">Infrastructure</a>
                <a href="/api/kubernetes/status">Kubernetes</a>
                <a href="/api/cost/status">Cost</a>
                <a href="/api/security/status">Security</a>
                <a href="/api/cicd/status">CI/CD</a>
                <a href="/api/monitoring/status">Monitoring</a>
            </div>
        </footer>
    </main>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Request lifecycle hooks
# ---------------------------------------------------------------------------

@app.before_request
def _count_request() -> None:
    """Increment the in-memory request counter before every request."""
    _increment_requests()


@app.after_request
def _log_request(response):
    """Emit a structured log line for every completed HTTP request.

    The format mirrors what gunicorn's access log produces so that
    `docker logs` and `kubectl logs` remain easy to parse.
    """
    logger.info(
        "Request completed | method=%s path=%s status=%d ip=%s",
        request.method,
        request.path,
        response.status_code,
        request.remote_addr,
    )
    return response


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def dashboard() -> str:
    payload = _environment_payload()
    cost = get_cost_status()
    security = get_security_status()
    status = payload["status"]

    status_class = {
        "RUNNING": "",
        "WARNING": "warn",
        "DESTROYING": "destroy",
        "OFFLINE": "off",
    }.get(status, "")

    return render_template_string(
        DASHBOARD_TEMPLATE,
        app_name=APP_NAME,
        app_version=APP_VERSION,
        environment=payload["environment"],
        hostname=socket.gethostname(),
        uptime=format_uptime(payload["uptimeSeconds"]),
        status=status,
        status_class=status_class,
        component_status="RUNNING" if status in ("RUNNING", "WARNING") else "OFFLINE",
        savings_percent=cost["savingsPercent"],
        events=lifecycle_events[:6],
        security_checks=security["checks"],
        security_passing=security["passing"],
        security_total=security["total"],
        current_time=datetime.now(timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
    )


@app.get("/health")
def health() -> tuple[Any, int]:
    return jsonify(
        {
            "status": "healthy",
            "service": APP_NAME,
            "version": APP_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    ), 200


@app.get("/ready")
def readiness() -> tuple[Any, int]:
    checks = {
        "application": True,
        "runtime": True,
        "configuration": bool(APP_NAME and APP_VERSION),
    }

    ready = all(checks.values())

    return jsonify(
        {
            "status": "ready" if ready else "not_ready",
            "checks": checks,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    ), 200 if ready else 503


@app.get("/api/info")
def environment_info() -> tuple[Any, int]:
    """Return application metadata (name, version, env, hostname, Python, time)."""
    logger.info("API info request received")
    return jsonify(get_environment_info()), 200


@app.get("/metrics")
def metrics() -> tuple[Any, int]:
    """Simple application metrics endpoint for DevOps demonstration.

    Returns total request count, uptime, and current timestamp.
    No Prometheus client is required -- the payload is plain JSON.
    Suitable for polling from Grafana's JSON datasource or a simple
    shell health-check script.
    """
    uptime_seconds = round(time.time() - START_TIME, 2)
    logger.info("Metrics request received | uptime=%ss", uptime_seconds)
    return jsonify(
        {
            "application": APP_NAME,
            "version": APP_VERSION,
            "environment": ENVIRONMENT,
            "total_requests": _get_request_count(),
            "uptime_seconds": uptime_seconds,
            "uptime": format_uptime(uptime_seconds),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    ), 200


@app.get("/api/request")
def request_info() -> tuple[Any, int]:
    return jsonify(
        {
            "method": request.method,
            "path": request.path,
            "remote_address": request.remote_addr,
            "user_agent": request.headers.get(
                "User-Agent",
                "unknown",
            ),
            "forwarded_for": request.headers.get(
                "X-Forwarded-For",
                "not-provided",
            ),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    ), 200


# ---------------------------------------------------------------------------
# Platform API -- environment lifecycle
# ---------------------------------------------------------------------------

@app.get("/api/environment/status")
def environment_status() -> tuple[Any, int]:
    return jsonify(_environment_payload()), 200


@app.get("/api/environment/events")
def environment_events() -> tuple[Any, int]:
    return jsonify({"events": lifecycle_events[:20]}), 200


@app.post("/api/environment/start")
def environment_start() -> tuple[Any, int]:
    if environment_state["status"] in ("RUNNING", "WARNING"):
        return jsonify({"error": "Environment is already running"}), 409
    return jsonify(start_environment()), 200


@app.post("/api/environment/destroy")
def environment_destroy() -> tuple[Any, int]:
    if environment_state["status"] == "OFFLINE":
        return jsonify({"error": "Environment is already offline"}), 409
    return jsonify(destroy_environment()), 200


@app.post("/api/environment/restart")
def environment_restart() -> tuple[Any, int]:
    return jsonify(restart_environment()), 200


# ---------------------------------------------------------------------------
# Platform API -- infrastructure, kubernetes, cost, security, cicd, monitoring
# ---------------------------------------------------------------------------

@app.get("/api/infrastructure/status")
def infrastructure_status() -> tuple[Any, int]:
    return jsonify(get_infrastructure_status()), 200


@app.get("/api/kubernetes/status")
def kubernetes_status() -> tuple[Any, int]:
    return jsonify(get_kubernetes_status()), 200


@app.get("/api/cost/status")
def cost_status() -> tuple[Any, int]:
    return jsonify(get_cost_status()), 200


@app.get("/api/security/status")
def security_status() -> tuple[Any, int]:
    return jsonify(get_security_status()), 200


@app.get("/api/cicd/status")
def cicd_status() -> tuple[Any, int]:
    return jsonify(get_cicd_status()), 200


@app.get("/api/monitoring/status")
def monitoring_status() -> tuple[Any, int]:
    return jsonify(get_monitoring_status()), 200


@app.errorhandler(404)
def not_found(error: Exception) -> tuple[Any, int]:
    logger.warning("404 Not Found: %s", request.path)
    return jsonify(
        {
            "error": "not_found",
            "message": "The requested endpoint does not exist.",
            "path": request.path,
        }
    ), 404


@app.errorhandler(405)
def method_not_allowed(error: Exception) -> tuple[Any, int]:
    logger.warning(
        "405 Method Not Allowed: %s %s", request.method, request.path
    )
    return jsonify(
        {
            "error": "method_not_allowed",
            "message": f"Method {request.method} is not allowed for {request.path}.",
        }
    ), 405


@app.errorhandler(500)
def internal_server_error(error: Exception) -> tuple[Any, int]:
    # Log the full traceback so it appears in `docker logs` / `kubectl logs`.
    logger.exception("Unhandled application error: %s", error)
    return jsonify(
        {
            "error": "internal_server_error",
            # Avoid leaking exception details to the client in production.
            "message": "An unexpected error occurred.",
        }
    ), 500


# ---------------------------------------------------------------------------
# Graceful shutdown
#
# Kubernetes sends SIGTERM before terminating a pod.  Catching it here
# gives in-flight requests a chance to complete before the process exits.
# Gunicorn also handles this signal, but registering it ourselves ensures
# the log line appears even when running via `python app.py`.
# ---------------------------------------------------------------------------

def _handle_sigterm(signum, frame) -> None:  # noqa: ANN001
    logger.info("SIGTERM received -- initiating graceful shutdown")
    sys.exit(0)


signal.signal(signal.SIGTERM, _handle_sigterm)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))

    # Security: never enable debug mode in production.
    # Set FLASK_DEBUG=true ONLY in a local development environment.
    # In Docker / Kubernetes the application is served by gunicorn (see
    # Dockerfile CMD), so this block is only reached during local testing.
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    if debug and ENVIRONMENT == "production":
        logger.warning(
            "FLASK_DEBUG=true is set but ENVIRONMENT=production -- "
            "debug mode has been forcibly disabled for security."
        )
        debug = False

    logger.info("Starting development server on 0.0.0.0:%d", port)
    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug,
    )