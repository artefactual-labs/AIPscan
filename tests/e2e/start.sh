#!/usr/bin/env bash
set -euo pipefail

flask db upgrade
flask db check
flask storage-service-bootstrap \
    --name ambox --url http://ambox:64081 \
    --username test --api-key test --default

celery -A AIPscan.worker.celery worker --concurrency=4 --loglevel=info &
exec gunicorn --bind 0.0.0.0:5000 --timeout 120 'AIPscan:create_app()'
