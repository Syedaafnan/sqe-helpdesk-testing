#!/usr/bin/env bash
# Availability failure-and-recovery test (docs/team/PERFORMANCE.md, REC-6).
# One k6 virtual user runs the W1+W2 iteration for 90 s. At t=30 s the
# application server is stopped (simulated crash), at t=45 s it is started
# again. The k6 per-request log is analysed for: first failure, last failure,
# outage seen by the user, time to first success after restart, and whether
# every ticket created after recovery passes the read-back check.
#
# usage: bash tests/team/perf/outage_recovery.sh /path/to/k6
# Requires the demo site on :8080 started from this repository (WSL/Linux).
set -euo pipefail
K6="${1:-k6}"
cd "$(dirname "$0")/../../.."
OUT=docs/team/evidence/performance
LOG="$OUT/outage_points.json"
EVENTS="$OUT/outage_events.txt"
: > "$EVENTS"
stamp() { python3 -c 'import time;print(f"{time.time():.3f}")'; }

"$K6" run -q -e VUS=1 -e DURATION=90s -e RUN=outage --out json="$LOG" tests/team/perf/helpdesk_load.js > /dev/null 2>&1 &
K6_PID=$!
echo "k6_start $(stamp)" >> "$EVENTS"
sleep 30
pkill -f "runserver 0.0.0.0:8080"
echo "server_killed $(stamp)" >> "$EVENTS"
sleep 15
nohup python manage.py runserver 0.0.0.0:8080 --noreload > "$HOME/runserver.log" 2>&1 &
echo "server_restarted $(stamp)" >> "$EVENTS"
for _ in $(seq 1 30); do curl -sf -o /dev/null http://localhost:8080/ && break; sleep 1; done
echo "server_ready $(stamp)" >> "$EVENTS"
set +e
wait "$K6_PID"
set -e

python3 - "$LOG" "$EVENTS" <<'EOF' | tee "$OUT/outage_recovery.txt"
import json, sys
from datetime import datetime
log, events = sys.argv[1], sys.argv[2]
ev = {k: float(v) for k, v in (l.split() for l in open(events))}
reqs = []
for line in open(log):
    p = json.loads(line)
    if p.get("type") == "Point" and p["metric"] == "http_req_failed":
        t = datetime.fromisoformat(p["data"]["time"].replace("Z", "+00:00")).timestamp()
        reqs.append((t, p["data"]["value"], p["data"]["tags"].get("name", "?")))
checks = [json.loads(l) for l in open(log) if '"metric":"checks"' in l and '"type":"Point"' in l]
fails = [r for r in reqs if r[1] == 1]
t0, kill, restart = ev["k6_start"], ev["server_killed"], ev["server_restarted"]
print("Availability failure and recovery (1 VU, 90 s; server stopped at ~30 s, restarted at ~45 s)")
print(f"requests: {len(reqs)}, failed: {len(fails)}")
print(f"server killed at   t={kill - t0:6.1f} s")
print(f"server restarted   t={restart - t0:6.1f} s")
print(f"server ready       t={ev['server_ready'] - t0:6.1f} s")
if fails:
    first, last = fails[0][0], fails[-1][0]
    after = [r for r in reqs if r[0] > last and r[1] == 0]
    print(f"first failure      t={first - t0:6.1f} s  ({fails[0][2]})")
    print(f"last failure       t={last - t0:6.1f} s")
    print(f"user-visible outage: {last - first:.1f} s")
    if after:
        print(f"first success after restart t={after[0][0] - t0:6.1f} s -> recovery {after[0][0] - restart:.1f} s after restart")
        print(f"requests after recovery: {len(after)}, failed after recovery: {sum(1 for r in reqs if r[0] > after[0][0] and r[1] == 1)}")
ok_after = [c for c in checks if datetime.fromisoformat(c['data']['time'].replace('Z','+00:00')).timestamp() > ev['server_ready']]
print(f"functional checks after recovery: {sum(c['data']['value'] for c in ok_after):.0f}/{len(ok_after)} passed")
EOF
rm -f "$LOG"
