#!/usr/bin/env bash
set -euo pipefail

flask db upgrade
flask db check
flask storage-service-bootstrap \
    --name ambox --url http://ambox:64081 \
    --username test --api-key test --default
flask storage-service-bootstrap \
    --name boundary --url http://fault-storage:8000 \
    --username test --api-key test

celery -A AIPscan.worker.celery worker --concurrency=4 --loglevel=info &
worker_pid=$!
gunicorn --bind 0.0.0.0:5000 --timeout 120 --chdir /e2e web:application &
web_pid=$!

# A listening web port must not hide a dead worker.
trap 'kill "$worker_pid" "$web_pid" 2>/dev/null || true' EXIT
wait -n "$worker_pid" "$web_pid"
exit 1
