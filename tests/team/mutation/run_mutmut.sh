#!/usr/bin/env bash
# Mutation testing with mutmut on two team-owned modules:
#   rules      src/helpdesk/ticket_rules.py    (critical business-rule module)
#   generator  tests/team/datagen/generate.py  (decides what the API tests send)
#
# Run it in a virtualenv WITHOUT helpdesk installed (an editable install would
# shadow the mutated copy):
#   python -m venv v && v/bin/pip install pytest mutmut==3.8.1 PyYAML
#
# Each target gets a small isolated workspace (module + its unit tests only)
# so mutmut does not copy the whole Django project. Results are written to
# docs/team/evidence/mutation/<target>_*.txt
#
# usage: bash tests/team/mutation/run_mutmut.sh [min_score_percent] [targets...]
# exits 1 if any target's mutation score is below the threshold (CI gate).
set -euo pipefail

MIN_SCORE="${1:-80}"
if [ "$#" -gt 0 ]; then shift; fi
TARGETS="${*:-rules generator}"
REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
BASE="${MUTMUT_WORKDIR:-${TMPDIR:-/tmp}/mutwork}"
OUT="$REPO/docs/team/evidence/mutation"
mkdir -p "$OUT"
status=0

setup_rules() {
  mkdir -p src/helpdesk tests
  touch src/helpdesk/__init__.py
  cp "$REPO/src/helpdesk/ticket_rules.py" src/helpdesk/
  cp "$REPO/tests/team/unit/test_ticket_rules.py" tests/
  SOURCE='src/helpdesk/ticket_rules.py'
  TESTDIR='tests/'
  # UT-00 compares against the Django settings module, which is not in this workspace.
  EXTRA='"-k", "not flow_copy_matches"'
}

setup_generator() {
  mkdir -p src/tests/team/datagen gen_tests
  touch src/tests/__init__.py src/tests/team/__init__.py src/tests/team/datagen/__init__.py
  cp "$REPO/tests/team/datagen/generate.py" src/tests/team/datagen/
  cp "$REPO/tests/team/datagen/test_generate.py" gen_tests/
  SOURCE='src/tests/team/datagen/generate.py'
  TESTDIR='gen_tests/'
  EXTRA='"-q"'
}

for target in $TARGETS; do
  WORK="$BASE/$target"
  rm -rf "$WORK" && mkdir -p "$WORK" && cd "$WORK"
  "setup_$target"
  cat > pyproject.toml <<EOF
[tool.mutmut]
source_paths = ["$SOURCE"]
pytest_add_cli_args_test_selection = ["$TESTDIR"]
also_copy = ["$TESTDIR"]
pytest_add_cli_args = ["-p", "no:django", "-p", "no:cacheprovider", $EXTRA]

[tool.pytest.ini_options]
markers = ["unit: white-box unit tests"]
EOF

  echo "== mutmut: $target ($SOURCE)"
  # mutmut exits non-zero when mutants survive; the score is checked below,
  # so record the exit code instead of failing here.
  set +e
  mutmut run > "$OUT/${target}_run.log" 2>&1
  run_rc=$?
  mutmut results --all true > "$OUT/${target}_results.txt" 2>&1
  set -e
  echo "mutmut run exit code: $run_rc"
  if ! grep -qE ": (killed|survived|timeout)$" "$OUT/${target}_results.txt"; then
    echo "mutmut produced no results:"; tail -20 "$OUT/${target}_run.log"; exit 1
  fi

  # one diff per surviving mutant, for the survivor analysis
  : > "$OUT/${target}_surviving.diff"
  grep -E ": survived$" "$OUT/${target}_results.txt" | awk -F: '{print $1}' | sed 's/^ *//' | while read -r m; do
    echo "### $m" >> "$OUT/${target}_surviving.diff"
    mutmut show "$m" >> "$OUT/${target}_surviving.diff" 2>&1
    echo >> "$OUT/${target}_surviving.diff"
  done

  python3 - "$OUT/${target}_results.txt" "$MIN_SCORE" "$target" <<'EOF' | tee "$OUT/${target}_summary.txt" || status=1
import collections, sys
path, minimum, target = sys.argv[1], float(sys.argv[2]), sys.argv[3]
status = collections.Counter(
    line.rsplit(":", 1)[1].strip() for line in open(path) if ": " in line
)
killed = status["killed"] + status["timeout"]
total = sum(status.values()) - status["skipped"]
score = 100.0 * killed / total if total else 0.0
print(f"{target}: {dict(status)}")
print(f"{target}: mutation score = {killed}/{total} = {score:.1f}% (gate: >= {minimum:.0f}%)")
sys.exit(0 if total and score >= minimum else 1)
EOF
done
rm -f "$OUT/mutmut_results.txt" "$OUT/mutmut_summary.txt" "$OUT/surviving_mutants.diff"
exit $status
