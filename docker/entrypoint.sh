#!/usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset

#__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case $1 in
    '')
        echo "Usage: (convenience shortcuts)"
        echo "  ./entrypoint.sh worker      Execute worker."
        exit 0
        ;;
    'worker')
        exec celery worker -A AIPscan.worker.celery --loglevel=info
        ;;
    'aipscan')
        exec python run.py
        ;;
esac

exec "${@}"
