# Mutation Testing

**Tools:** mutmut 3.8.1 (built-in operators) plus two project-specific
operators in [`tests/team/mutation/custom_operators.py`](../../tests/team/mutation/custom_operators.py).
**How to run:** `bash tests/team/mutation/run_mutmut.sh 90` and
`python tests/team/mutation/custom_operators.py --min-score 100`, in a
virtualenv without helpdesk installed (an editable install would shadow the
mutated copy). Both run in CI as the `mutation-tests` gate.

## 1. Targets

| Target | Why | Tests used |
|---|---|---|
| `src/helpdesk/ticket_rules.py` | Critical business-rule module (BR-1 to BR-4), used by every write path after the fixes | `tests/team/unit/test_ticket_rules.py` (UT-01..UT-28) |
| `tests/team/datagen/generate.py` | Decides which values the API suite sends and whether each must be accepted: a wrong generator silently weakens 100 API tests | `tests/team/datagen/test_generate.py` (GEN-01..GEN-33) |

Each target is copied into an isolated workspace with only its unit tests, so
mutmut does not copy the whole Django project and each mutant runs in under a
second.

## 2. Custom operators

| Operator | What it does | Fault it models |
|---|---|---|
| **BSO** Boundary Shift Operator | For each comparison that uses a named limit (`PRIORITY_MIN`, `PRIORITY_MAX`, `TITLE_MAX_LENGTH`), replaces the limit **at the point of use** by `limit + 1` and `limit - 1`. The constant and the error message stay correct. | Off-by-one at a BR-1 boundary. mutmut can only change the constant itself, which also changes the message and is easier to kill. |
| **GDO** Guard Deletion Operator | (a) Deletes each guard `if <cond>: raise/return`. (b) Drops each operand of every `and`/`or` in turn. | A write path that skips a rule check, which is exactly what DEF-01, DEF-02, DEF-06 and DEF-10 are. |

BSO produced 6 mutants and GDO produced 24.

## 3. Results across three runs

| Run | What changed | rules (mutmut) | generator (mutmut) | custom BSO+GDO |
|---|---|---|---|---|
| Run 1 (baseline) | first run against the existing tests | 116/124 killed = **93.5 %** (8 survived) | 875/1012 = **86.5 %** (137 survived) | 28/30 = **93.3 %** (2 survived) |
| Run 2 | added UT-26..UT-28 and GEN-27..GEN-33 to kill the killable survivors | 121/124 = **97.6 %** (3) | 997/1012 = **98.5 %** (15) | 30/30 = **100 %** |
| Run 3 | added one assertion to GEN-19 (survivor `generate_69`) | 121/124 = **97.6 %** (3) | 998/1012 = **98.6 %** (14) | 30/30 = **100 %** |

**Surviving mutants analysed: 147 in run 1** (8 + 137 + 2). 130 were killable
and were killed by new tests; the 17 that remain are equivalent or change only
help text (below). Evidence: `evidence/mutation/run1_before_kill/`,
`run2_after_kill/`, `run3_final/` (results, one diff per survivor, summaries).

## 4. Survivor analysis

Verdicts: **K** = killable, killed by the named test; **E** = equivalent (no
input can tell the mutant from the original); **C** = cosmetic (changes only
`--help` text, accepted).

### 4.1 `ticket_rules.py` (mutmut, run 1: 8 survivors)

| # | Mutant | Change | Verdict | Reason / killing test |
|---|---|---|---|---|
| S1 | `validate_title__mutmut_5` | message `"Enter a summary..."` → `None` | K | The message is what the user reads but no test pinned it. **UT-26** asserts the exact text. |
| S2 | `validate_title__mutmut_10` | message → `"XXEnter a summary...XX"` | K | UT-26 |
| S3 | `validate_title__mutmut_11` | message lower-cased | K | UT-26 |
| S4 | `validate_title__mutmut_12` | message upper-cased | K | UT-26 |
| S5 | `check_status_change__mutmut_18` | dependency message lower-cased | K | UT-26 pins the dependency message too. |
| S6 | `allowed_next_statuses__mutmut_3` | `flow.get(current, ())` → `flow.get(current, None)` | E | Both defaults are falsy, so the next line returns `tuple(all_statuses)` either way. |
| S7 | `allowed_next_statuses__mutmut_5` | `flow.get(current, ())` → `flow.get(current)` | E | Same as S6: the default `None` is falsy. |
| S8 | `check_status_change__mutmut_37` | `allowed_next_statuses(current, flow, all_statuses)` → `(..., None)` inside the error message | E | Only reached when the transition is not allowed. If `current` had no flow entry the fallback (all statuses) would allow every valid `new`, so the branch that builds the message is never reached with an empty flow entry and `all_statuses` is never read. |

### 4.2 Custom operators (run 1: 2 survivors)

| # | Mutant | Change | Verdict | Reason / killing test |
|---|---|---|---|---|
| S9 | GDO C06 | deletes `if new not in all_statuses: return False` in `is_transition_allowed` | K | Only observable when `current == new` and both are unknown codes: the mutant then returns True. **UT-27** (`is_transition_allowed(99, 99)` is False). Real meaning: a ticket left with a removed status could "keep" it. |
| S10 | GDO C07 | deletes `if new == current: return True` | K | With the shipped flow every status lists itself, so it was invisible. **UT-28** uses a custom flow without self-loops: keeping the status (a comment) must still be allowed. This matters because the flow is a setting that deployments override. |

### 4.3 `generate.py` (mutmut, run 1: 137 survivors, grouped)

| # | Group (count) | Example | Verdict | Reason / killing test |
|---|---|---|---|---|
| S11 | Record metadata swapped (≈100) | `case(None, schema, field, "EP", ...)`, `"EP"` → `"XXEPXX"` / `"ep"`, `schema` → `None` | K | GEN-06..GEN-17 compared value and validity per partition but not the routing fields. **GEN-27** checks operation, schema, field, technique and id on every record of every generator. |
| S12 | `wrong_type` value swapped (3) | `"abc"` → `None`, `"XXabcXX"`, `"ABC"` | K | **GEN-28** pins the exact value (`None` would test "null", a different partition). |
| S13 | enum value → `None` (1) | `case(..., f"enum_{v}", None, True)` | K | GEN-28 |
| S14 | `(lo + hi) // 2` → `/ 2` (1) | mid = 3.0 | K | `3.0 == 3` in Python, so equality tests passed, but JSON sends `3.0`, which the API would see as a fraction in a "valid" case. **GEN-29** asserts `type(mid) is int`. A real latent fault, found only by mutation testing. |
| S15 | `valid` flag → `None` (2) | string `wrong_type` valid `None`; `null` case valid `None` | K | `None` is falsy, so `not valid` checks passed. **GEN-27** (`isinstance(valid, bool)`) and GEN-19 (run 3). |
| S16 | boolean partition renames (9) | `"true"` → `"TRUE"`, `None` | K | GEN-28 asserts the partition list. |
| S17 | `operations()` method literals (4) | `"put"` → `"PUT"`, `"patch"` → `"XXpatchXX"` | K | The test spec had no PUT/PATCH with a body. **GEN-30** adds one. |
| S18 | `schema.get("required", [])` → `None` / no default (2) | | K | GEN-30 uses a schema without `required`. |
| S19 | `main()` defaults → `None` (4) | `--spec`/`--out` default `None` | K | **GEN-31** calls `main([])`. |
| S20 | `mkdir(parents, exist_ok)` and `json indent` (8) | `parents=False`, `exist_ok=None`, `indent=3` | K | **GEN-32** writes into a new nested directory twice and checks the file layout. |
| S21 | diff output join (1) | `"\n".join` → `"XX\nXX".join` | K | **GEN-33** |
| S22 | `text_of_length__mutmut_1` | `if n <= 0` → `if n < 0` | E | For `n = 0` the slice `[:0]` returns `""` anyway. |
| S23 | `text_of_length__mutmut_8` | repeat count `+ 1` → `+ 2` | E | One extra repetition is cut off by `[:n]`. |
| S24 | `resolve__mutmut_5` | `lstrip("#/")` → `lstrip("XX#/XX")` | E | `lstrip` takes a character set; `X` never starts a JSON-pointer `$ref`. |
| S25 | `generate__mutmut_7`, `_10` | `rsplit("/", 1)` → `rsplit("/")`, `rsplit("/", 2)` | E | `[-1]` is the last segment in every case. |
| S26 | `generate__mutmut_11` | `[-1]` → `[+1]` | E | `rsplit("/", 1)` always returns two parts, so index 1 is index -1. |
| S27 | `main__mutmut_2`, `_3`, `_23`, `_27`, `_31`..`_34` (8) | `ArgumentParser(description=None)`, `metavar=("old", ...)` | C | Change only `--help` output; behaviour identical. Accepted rather than adding a brittle help-text test. |

## 5. What mutation testing found that coverage did not

Both modules had **100 % statement and branch coverage before run 1**. Coverage
was not proof of strong tests:

1. **S14**: an integer-vs-float latent fault in the generator that would have
   produced a mislabelled "valid" case.
2. **S9/S10**: two guards in the status-flow rule that the shipped flow made
   invisible; a deployment with its own flow could break the rule unnoticed.
3. **S11**: about 100 mutants showed that the per-type generator tests ignored
   the fields the API tests use to route each case.

## 6. CI gate

`mutation-tests` fails the pull request if either mutmut score drops below
**90 %** or any custom-operator mutant survives. The blocked pull request in
[CI.md](CI.md) shows the gate failing on a boundary change.
