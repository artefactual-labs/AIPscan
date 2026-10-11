#!/usr/bin/env bash
set -euo pipefail

# Export from the client: exports inside a module stay in its runtime.
result_dir="${AIPSCAN_RESULT_PATH:-output/e2e/$(date -u +%Y%m%dT%H%M%S)-$RANDOM}"
dagger --lock="${DAGGER_LOCK_MODE:-frozen}" call test-results "$@" export --path "$result_dir"
printf 'Acceptance artifacts: %s\n' "$result_dir"
cat "$result_dir/pytest.log"
cat "$result_dir/pytest-errors.log" >&2
exit "$(cat "$result_dir/exit-code")"
