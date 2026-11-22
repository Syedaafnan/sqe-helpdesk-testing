# Static Analysis

## 1. SonarQube

| Item | Value |
|---|---|
| Server | SonarQube Community Build 26.10.0.133078 (local, WSL; same version as the CI service container) |
| Scanner | sonar-scanner 7.2.0.5079, [`sonar-project.properties`](../../sonar-project.properties) |
| Scope | `src/helpdesk` (excluding migrations, static files, translations, upstream tests); tests: `tests/team`; coverage from `coverage.xml` (team suite) |
| Evidence | `evidence/sonar/*.json` (API exports), `evidence/sonar/scanner.log` |

### 1.1 Project measures (analysis of 2026-11-22, quality gate **Passed**)

| Measure | Value | Measure | Value |
|---|---|---|---|
| Lines of code (ncloc) | 14 552 | Files / functions | 148 / 427 |
| Cyclomatic complexity (total) | 1 386 | Cognitive complexity | 1 529 |
| Coverage (team suite) | 39.3 % (line 45.1 %, branch 18.6 %) | Duplicated lines | 1.4 % |
| Bugs | 12 (Reliability rating **D**) | Vulnerabilities | 17 (Security rating **D**) |
| Code smells | 12 (Maintainability **A**, debt 111 min) | Security hotspots | 0 |

The quality gate ("Sonar way") judges **new code**, i.e. the team's changes. It
passed because the team code has no new issues and is well covered
(`ticket_rules.py`: 100 % coverage, 0 code smells). The D ratings come from
upstream code.

### 1.2 Team module

| File | ncloc | Complexity | Cognitive | Coverage | Branch coverage | Issues |
|---|---|---|---|---|---|---|
| `src/helpdesk/ticket_rules.py` | 75 | **26** | 18 | **100 %** | **100 %** | 0 |

### 1.3 Most complex files (where the defects are)

| File | Complexity | ncloc | Coverage | Team defects in this file |
|---|---|---|---|---|
| `views/staff.py` | 259 | 1 873 | 20.4 % | DEF-06, DEF-09, DEF-10, DEF-14 |
| `models.py` | 212 | 1 644 | 61.3 % | – |
| `email.py` | 147 | 897 | 0.0 % | out of scope |
| `update_ticket.py` | 90 | 364 | 60.5 % | DEF-13 |
| `forms.py` | 87 | 643 | 48.7 % | DEF-04 (field name) |
| `views/public.py` | 61 | 333 | 31.7 % | DEF-12 |
| `query.py` | 42 | 221 | 18.2 % | – |
| `serializers.py` | 42 | 253 | 74.7 % | DEF-01, DEF-02, DEF-03, DEF-05 |

The two most complex view/service modules (`staff.py`, `update_ticket.py`)
hold 5 of the 16 defects, which supports complexity as a risk indicator.

### 1.4 Open bugs and vulnerabilities reviewed (29)

| Rule | Type / severity | Count | Assessment |
|---|---|---|---|
| `Web:InputWithoutLabelCheck` | Bug, Major | 8 | Same issue class as DEF-15 (inputs without labels) on other templates; the fixed lookup form no longer appears. Accessibility backlog. |
| `Web:S5247` (autoescape disabled) | Vulnerability, Major | 8 | Templates using `|safe`/`autoescape off` for rendered Markdown; content is sanitised by `nh3` upstream. Reviewed, accepted. |
| `python:S3752` (HTTP methods not restricted) | Vulnerability, Minor | 6 | Views accepting GET and POST; low risk. |
| `python:S4502` (CSRF disabled) | Vulnerability, **Critical** | 1 | `CreateTicketIframeView` is `csrf_exempt` so the form can be embedded in other sites. Lets a third-party page create tickets for anonymous visitors (spam), not change existing data. Accepted by design, documented. |
| `Web:S7930` (duplicate `id`) | Bug, **Critical** | 1 | `include/unassigned.html` uses `id="dataTable"` twice: real but cosmetic (DataTables init on the dashboard). |
| others | Bug/Vulnerability | 5 | single occurrences in upstream JS/templates |

Exports: `evidence/sonar/project_measures.json`, `ticket_rules_measures.json`,
`files_measures.json`, `bugs_vulnerabilities.json`, `issues_facets.json`,
`quality_gate.json`.

## 2. Hand-calculated cyclomatic complexity

### 2.1 Whole module `ticket_rules.py`

Rule used (the same one SonarQube uses for Python): CC = 1 per function
+ 1 per `if`/`elif`/loop + 1 per `and`/`or` operator.

| Function | Decision points | CC |
|---|---|---|
| `RuleViolation.__init__` | none | 1 |
| `validate_priority` | `if … or …` (2), `if … or …` (2) | 5 |
| `validate_title` | `if … or …` (2), `if` (1) | 4 |
| `allowed_next_statuses` | `if` (1) | 2 |
| `is_transition_allowed` | `if` (1), `if` (1) | 3 |
| `submitter_may_change_status` | `or` (1), `and` (1) | 3 |
| `check_status_change` | `if` (1), `if … and …` (2), `if` (1) | 5 |
| `can_use_staff_api` | `and` (1), `and` (1) | 3 |
| **Total** | | **26** |

SonarQube reports **complexity = 26** for `src/helpdesk/ticket_rules.py`
(`evidence/sonar/ticket_rules_measures.json`): **the hand count matches exactly.**
(The `try/except` in `validate_priority` adds no point under this rule, and
SonarQube agrees.)

### 2.2 Control-flow graph of `check_status_change` (critical function)

```python
def check_status_change(current, new, has_open_dependencies, flow, all_statuses):
    if new not in all_statuses:                                  # N1
        raise RuleViolation("status_invalid", ...)               # R1
    if new != current and has_open_dependencies:                 # N2 (new != current), N3 (deps)
        raise RuleViolation("dependencies_open", ...)            # R2
    if not is_transition_allowed(current, new, flow, all_statuses):  # N4
        allowed = sorted(...)                                    # N5
        raise RuleViolation("transition_not_allowed", ...)       #   (N5)
    return new                                                   # RET
```

Each atomic condition is its own decision node (short-circuit `and`):

```
                 ┌──────┐
                 │  N1  │ new not in all_statuses ?
                 └──┬───┘
              T ┌───┴───┐ F
                ▼       ▼
             ┌────┐  ┌──────┐
             │ R1 │  │  N2  │ new != current ?
             └─┬──┘  └──┬───┘
               │     T ┌┴──────────┐ F
               │       ▼           │
               │    ┌──────┐       │
               │    │  N3  │ has_open_dependencies ?
               │    └──┬───┘       │
               │   T ┌─┴──┐ F      │
               │     ▼    └──────┐ │
               │  ┌────┐         ▼ ▼
               │  │ R2 │      ┌──────┐
               │  └─┬──┘      │  N4  │ not is_transition_allowed ?
               │    │         └──┬───┘
               │    │       T ┌──┴───┐ F
               │    │         ▼      ▼
               │    │      ┌────┐ ┌─────┐
               │    │      │ N5 │ │ RET │
               │    │      └─┬──┘ └──┬──┘
               ▼    ▼        ▼       ▼
               └────┴────► [ EXIT ] ◄┘
```

| Measure | Count |
|---|---|
| Nodes N | 9 (N1, R1, N2, N3, R2, N4, N5, RET, EXIT) |
| Edges E | 12 (N1→R1, N1→N2, N2→N3, N2→N4, N3→R2, N3→N4, N4→N5, N4→RET, R1→EXIT, R2→EXIT, N5→EXIT, RET→EXIT) |
| **V(G) = E − N + 2** | 12 − 9 + 2 = **5** |
| Predicate nodes P | 4 (N1, N2, N3, N4) → V(G) = P + 1 = **5** |
| Regions in the planar graph | **5** |

All three methods agree: **CC = 5**, the same as the function's share of
SonarQube's 26.

### 2.3 Basis paths and the tests that execute them

| Path | Route | Meaning | Unit test |
|---|---|---|---|
| P1 | N1(T) → R1 | status code does not exist | UT-21 `check_status_change(OPEN, 9, …)` → `status_invalid` |
| P2 | N1(F) → N2(F) → N4(F) → RET | status unchanged (comment only), even with open dependencies | UT-20 `(OPEN, OPEN, deps=True)` → OPEN |
| P3 | N1(F) → N2(T) → N3(T) → R2 | change blocked by open dependency | UT-22 `(OPEN, RESOLVED, deps=True)` → `dependencies_open`; UT-26 (message) |
| P4 | N1(F) → N2(T) → N3(F) → N4(F) → RET | allowed change | UT-19 `(OPEN, RESOLVED, deps=False)` → RESOLVED |
| P5 | N1(F) → N2(T) → N3(F) → N4(T) → N5 | change not in the flow | UT-23 `(CLOSED, RESOLVED, deps=False)` → `transition_not_allowed` |

Five independent paths, five tests: the basis-path set is complete. Together
with the rest of the suite this gives 100 % statement and branch coverage of
the module (48 statements, 20 branches).
