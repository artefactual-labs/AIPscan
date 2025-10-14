#!/usr/bin/env bash

set -euo pipefail
IFS=$'\n\t'

# Drop a leading "--" if present.
[[ "${1:-}" == "--" ]] && shift

# No args: Print help message and exit.
if [[ $# -eq 0 ]]; then
  cat >&2 <<'EOF'
Welcome to the AIPscan container image!

This container is a ready-to-use environment for AIPscan. It includes Python,
the full AIPscan source code, and a fully configured virtual environment.

We include Gunicorn to serve the application over HTTP, and Celery so you can
run the AIPscan worker. For example, you might run the following command to
start the web server:

  gunicorn --preload -t 300 --workers 3 --bind 0.0.0.0:5000 "AIPscan:create_app()"

Or you might run the following command to start a Celery worker:

  celery -A AIPscan.worker.celery worker --loglevel=info

To apply database migrations, you can run:

  flask db upgrade

Or any other command available in the environment, e.g.:

  python -V

EOF
  exit 0
fi

# Run the provided command.
exec "$@"
