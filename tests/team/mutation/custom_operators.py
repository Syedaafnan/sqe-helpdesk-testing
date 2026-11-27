"""Two project-specific mutation operators for src/helpdesk/ticket_rules.py.

mutmut's built-in operators change literals, operators and names one token at
a time. The two operators below model the faults this project actually found
or is most exposed to:

BSO  Boundary Shift Operator
     Every comparison that uses a named limit (PRIORITY_MIN, PRIORITY_MAX,
     TITLE_MAX_LENGTH) gets that limit replaced by (limit + 1) and (limit - 1)
     at the point of use. Models an off-by-one at a BR-1 boundary; the limit
     constant itself (and so the error message) stays correct, which a
     literal mutation of the constant cannot express.

GDO  Guard Deletion Operator
     (a) Every guard statement `if <cond>: raise ... / return ...` is removed.
     (b) Every operand of an `and` / `or` condition is dropped in turn.
     Models a write path that skips a rule check, which is exactly what
     DEF-01 / DEF-02 were (the staff API skipped the BR-2/BR-3 checks).

Each mutant is written into an isolated workspace and the unit tests are run
against it. Results go to docs/team/evidence/mutation/custom_operators.{json,md}.

usage (in a virtualenv WITHOUT helpdesk installed, see run_mutmut.sh):
    python tests/team/mutation/custom_operators.py [--min-score 80]
"""

import argparse
import ast
import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
MODULE = REPO / "src" / "helpdesk" / "ticket_rules.py"
TESTS = REPO / "tests" / "team" / "unit" / "test_ticket_rules.py"
OUT = REPO / "docs" / "team" / "evidence" / "mutation"
LIMITS = {"PRIORITY_MIN", "PRIORITY_MAX", "TITLE_MAX_LENGTH"}
PYTEST_ARGS = ["-q", "-x", "-p", "no:django", "-p", "no:cacheprovider", "-k", "not flow_copy_matches"]


def enclosing_function(tree, lineno):
    best = "<module>"
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.lineno <= lineno <= node.end_lineno:
            best = node.name
    return best


def sites(tree):
    """Yield (walk_index, operator, variant, line) for every mutation site."""
    for i, node in enumerate(ast.walk(tree)):
        if isinstance(node, ast.Compare):
            for side in [node.left, *node.comparators]:
                if isinstance(side, ast.Name) and side.id in LIMITS:
                    for delta in (+1, -1):
                        yield i, "BSO", f"{side.id}{delta:+d}", node.lineno
        if isinstance(node, ast.If) and node.body and isinstance(node.body[0], (ast.Raise, ast.Return)):
            yield i, "GDO", "delete-guard", node.lineno
        if isinstance(node, ast.BoolOp):
            for k in range(len(node.values)):
                yield i, "GDO", f"drop-operand-{k}", node.lineno


def mutate(tree, index, variant):
    t = copy.deepcopy(tree)
    nodes = list(ast.walk(t))
    node = nodes[index]
    if variant == "delete-guard":
        for parent in nodes:
            for field in ("body", "orelse"):
                block = getattr(parent, field, None)
                if isinstance(block, list) and node in block:
                    block[block.index(node)] = ast.Pass()
    elif variant.startswith("drop-operand-"):
        k = int(variant.rsplit("-", 1)[1])
        rest = [v for j, v in enumerate(node.values) if j != k]
        replacement = rest[0] if len(rest) == 1 else ast.BoolOp(op=node.op, values=rest)
        for parent in nodes:
            for field, value in ast.iter_fields(parent):
                if value is node:
                    setattr(parent, field, replacement)
                elif isinstance(value, list) and node in value:
                    value[value.index(node)] = replacement
    else:  # BSO: NAME+1 / NAME-1 at the comparison only
        name, delta = variant[:-2], int(variant[-2:])
        sides = [node.left, *node.comparators]
        for j, side in enumerate(sides):
            if isinstance(side, ast.Name) and side.id == name:
                shifted = ast.BinOp(
                    left=ast.Name(id=name, ctx=ast.Load()),
                    op=ast.Add() if delta > 0 else ast.Sub(),
                    right=ast.Constant(value=abs(delta)),
                )
                if j == 0:
                    node.left = shifted
                else:
                    node.comparators[j - 1] = shifted
    return ast.fix_missing_locations(t)


def changed_line(original_src, mutant_src):
    a, b = original_src.splitlines(), mutant_src.splitlines()
    for x, y in zip(a, b):
        if x.strip() != y.strip():
            return x.strip(), y.strip()
    return "", "(statement removed)"


def run_tests(workspace):
    r = subprocess.run(
        [sys.executable, "-m", "pytest", *PYTEST_ARGS, "tests"],
        cwd=workspace, capture_output=True, text=True, timeout=120,
    )
    return r.returncode


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--min-score", type=float, default=0.0)
    args = p.parse_args()

    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    baseline = ast.unparse(tree)

    workspace = Path(tempfile.mkdtemp(prefix="custom_mut_"))
    pkg = workspace / "src" / "helpdesk"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (workspace / "tests").mkdir()
    shutil.copy(TESTS, workspace / "tests")
    (workspace / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\npythonpath = ["src"]\nmarkers = ["unit: unit tests"]\n'
    )

    (pkg / "ticket_rules.py").write_text(baseline)
    if run_tests(workspace) != 0:
        sys.exit("unit tests fail on the unmutated module; fix them first")

    results = []
    for n, (index, operator, variant, line) in enumerate(sites(tree), start=1):
        mutant = ast.unparse(mutate(tree, index, variant))
        (pkg / "ticket_rules.py").write_text(mutant)
        code = run_tests(workspace)
        before, after = changed_line(baseline, mutant)
        results.append({
            "id": f"C{n:02d}",
            "operator": operator,
            "variant": variant,
            "function": enclosing_function(tree, line),
            "line": line,
            "original": before,
            "mutant": after,
            "status": "killed" if code != 0 else "survived",
        })
    shutil.rmtree(workspace, ignore_errors=True)

    killed = sum(r["status"] == "killed" for r in results)
    score = 100.0 * killed / len(results)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "custom_operators.json").write_text(json.dumps(results, indent=2))
    lines = [
        "| ID | Operator | Variant | Function | Line | Mutated code | Status |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        code = r["mutant"].replace("|", "\\|")
        lines.append(f"| {r['id']} | {r['operator']} | {r['variant']} | {r['function']} | {r['line']} | `{code}` | {r['status']} |")
    for op in ("BSO", "GDO"):
        sub = [r for r in results if r["operator"] == op]
        k = sum(r["status"] == "killed" for r in sub)
        lines.append(f"\n{op}: {k}/{len(sub)} killed")
    lines.append(f"\nCustom-operator mutation score = {killed}/{len(results)} = {score:.1f}%")
    (OUT / "custom_operators.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[-3:]))
    for r in results:
        if r["status"] == "survived":
            print(f"SURVIVED {r['id']} {r['operator']} {r['variant']} in {r['function']}: {r['mutant']}")
    sys.exit(0 if score >= args.min_score else 1)


if __name__ == "__main__":
    main()
