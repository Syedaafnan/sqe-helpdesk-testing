#!/usr/bin/env bash
# Runs the four required k6 runs: 1 user twice and 5 users twice, 75 s each,
# with a 15 s pause between runs. Results: docs/team/evidence/performance/.
# usage: bash tests/team/perf/run_k6.sh [path-to-k6]
# RESET_CMD (optional) runs before every run so each starts from the same data,
# e.g. RESET_CMD="python manage.py demo_data --reset" (the API cost grows with
# the number of tickets, DEF-16, so an unreset database skews later runs).
set -euo pipefail
K6="${1:-k6}"
cd "$(dirname "$0")/../../.."
status=0
for run in 1u_run1 1u_run2 5u_run1 5u_run2; do
  vus="${run%%u_*}"
  echo "== $run ($vus virtual users)"
  if [ -n "${RESET_CMD:-}" ]; then
    eval "$RESET_CMD" > /dev/null
    echo "   data reset: $(python manage.py shell -c 'from helpdesk.models import Ticket; print(Ticket.objects.count())' 2>/dev/null | tail -1) tickets"
  fi
  if ! "$K6" run -q -e VUS="$vus" -e RUN="$run" tests/team/perf/helpdesk_load.js > /dev/null 2>&1; then
    echo "   thresholds not met in $run"
    status=1
  fi
  cat "docs/team/evidence/performance/k6_${run}.txt"
  sleep 15
done
exit $status
