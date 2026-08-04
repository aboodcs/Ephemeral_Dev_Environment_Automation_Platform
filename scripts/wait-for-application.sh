#!/usr/bin/env bash

set -euo pipefail

# Health check configuration parameters
APP_URL="${1:-http://localhost:80/}"
MAX_ATTEMPTS="${2:-30}"
SLEEP_SECONDS="${3:-5}"

echo "=========================================="
echo "Running Application Health Check"
echo "Target URL: ${APP_URL}"
echo "Max Attempts: ${MAX_ATTEMPTS}, Sleep Interval: ${SLEEP_SECONDS}s"
echo "=========================================="

for attempt in $(seq 1 "${MAX_ATTEMPTS}"); do
    if curl --fail --silent --show-error "${APP_URL}" >/dev/null 2>&1; then
        echo "SUCCESS: Application is ready and returning HTTP 200 OK!"
        exit 0
    fi

    # Check /health endpoint as fallback if root URL check is pending
    if curl --fail --silent --show-error "${APP_URL%/}/health" >/dev/null 2>&1; then
        echo "SUCCESS: Application health endpoint is returning HTTP 200 OK!"
        exit 0
    fi

    echo "Application not ready yet. Attempt (${attempt}/${MAX_ATTEMPTS})"
    sleep "${SLEEP_SECONDS}"
done

echo "=========================================="
echo "ERROR: Application did not become ready after ${MAX_ATTEMPTS} attempts."
echo "Checked URL: ${APP_URL}"
echo "=========================================="

exit 1