# Test Plan: django-helpdesk (SE3002 Final Project)

| Item | Value |
|---|---|
| System under test | django-helpdesk, upstream commit `7bf832c` (tag `baseline`), BSD-3 |
| Team repository | https://github.com/Syedaafnan/sqe-helpdesk-testing |
| Plan version | 1.0, 2026-11-21 |
| Test basis | [SCOPE.md](SCOPE.md) (FR-01..FR-10, BR-1..BR-4, assumptions A1..A4), upstream docs (`docs/api.rst`), code |

## 1. Objectives

1. Verify the two workflows: **W1 Submit Ticket** and **W2 Update/Resolve Ticket**. Both share the record `Ticket.status`, and two roles take part (staff, customer/submitter).
2. Show that the four business rules hold on **every** path that changes the shared record.
3. Measure test quality, not only coverage, with MCC/MC-DC, mutation score and traceability.
4. Give a release / hold recommendation backed by measured exit criteria.

## 2. Scope

**In scope:** public ticket form, staff ticket form (create, respond), public
ticket view, REST API (`/api/tickets/`, `/api/followups/`,
`/api/user_tickets/`), Kanban status endpoint, role-based access, the team
rule module `ticket_rules.py`, non-functional qualities (performance at 1 and
5 users, recovery from a failed write, accessibility of W1 screens, security
headers and dependencies).

**Out of scope:** e-mail import (IMAP/POP), knowledge base, reports, saved
queries, checklists, attachments beyond the form field, translations,
production deployment (we test the development server with SQLite, as
seeded by `demo_data`).

## 3. Approach by test level

| Level / type | Technique | Tool | Location | Owner |
|---|---|---|---|---|
| Static analysis | SonarQube metrics; hand-calculated cyclomatic complexity of the critical function | SonarQube 26.10, sonar-scanner 7.2 | [STATIC_ANALYSIS.md](STATIC_ANALYSIS.md) | Member 1 |
| Unit (white box) | Statement + branch coverage 100 %; MCC and MC/DC for BR-2 (critical module) and BR-4; EP/BVA for BR-1; state table for BR-3 | pytest, coverage | `tests/team/unit/` | Member 1 |
| Test data generation | OpenAPI → EP + 3-point BVA; constraint change and regeneration | `generate.py` | `tests/team/datagen/` | Member 2 |
| API / integration | EP, BVA, decision table (BR-2), state transitions (BR-3), access (BR-4), repeated requests, read-back after every write, cross-workflow W1 → W2 | pytest-django, DRF APIClient | `tests/team/api/` | Member 2 |
| End-to-end | 4 use cases (2 per member), each main + 2 alternative + 2 exception | Playwright | `tests/team/e2e/` | Members 1–2 |
| Usability / accessibility | 2 task tests (rejected value then fix; keyboard only); axe-core and Lighthouse before/after a fix | Playwright, axe-core 4.10.2, Lighthouse 12.2.1 | `tests/team/e2e/` | Member 1 |
| Security | Access matrix (10 browser checks), ZAP passive scan, pip-audit | Playwright, ZAP 2.17, pip-audit | `tests/team/security/` | Member 2 |
| Performance | k6, 1 and 5 virtual users, 2 runs each, 75 s, p95 targets | k6 1.3 | `tests/team/perf/` | Member 2 |
| Reliability | Controlled failure (DB write rejected) and recovery (retry) | pytest + mock | `tests/team/api/test_recovery.py` | Member 2 |
| Mutation | mutmut + 2 custom operators; survivor analysis | mutmut 3.8.1 | `tests/team/mutation/` | Member 1 |
| Regression | Upstream suite (570 tests) on every change | Django test runner | `quicktest.py` | all |
| CI | Gates for tests, coverage, mutation, SonarQube, e2e | GitHub Actions | `.github/workflows/quality-gate.yml` | Member 2 |

**Defect handling.** Every defect gets a GitHub Issue with severity, steps,
expected/actual, evidence and the test that reproduces it
([DEFECTS.md](DEFECTS.md)). An open defect is pinned by an
`xfail(strict=True)` test. Fixes are made only where the team owns the change
(rule enforcement, accessibility); every fix has a test that fails before it
and passes after it.

## 4. Environment

| Component | Version |
|---|---|
| OS | Windows 11 + WSL2 Ubuntu 24.04 (Smart App Control blocks unsigned native wheels on Windows) |
| Python / Django / DRF | 3.12.3 / 6.1.3 / 3.18.3 |
| Database | SQLite (demo), seeded by `demo_data --seed 1476` (141 tickets) |
| Browser | Chromium 140 (Playwright 1.55); Chrome for Lighthouse |
| Accounts | admin, alice/bruno/chloe/kenji (staff), sam (customer); password in BASELINE.md |

Full setup and reset: [BASELINE.md](BASELINE.md).

## 5. Three-point estimation

E = (O + 4M + P) / 6, σ = (P − O) / 6, in person-hours.

| # | Task | O | M | P | E | σ |
|---|---|---|---|---|---|---|
| 1 | Select system, baseline, environment, seed data | 3 | 5 | 10 | 5.5 | 1.17 |
| 2 | Scope, requirements, business rules | 2 | 3 | 5 | 3.2 | 0.50 |
| 3 | Test plan, estimation, risks, exit criteria | 2 | 3 | 5 | 3.2 | 0.50 |
| 4 | Static analysis + hand CC | 1.5 | 2.5 | 5 | 2.8 | 0.58 |
| 5 | Rule module + unit tests (100 %, MCC, MC/DC) | 3 | 5 | 8 | 5.2 | 0.83 |
| 6 | OpenAPI spec + generator + constraint change | 3 | 4 | 7 | 4.3 | 0.67 |
| 7 | API tests (EP, BVA, DT, ST, repeats, read-back) | 4 | 6 | 10 | 6.3 | 1.00 |
| 8 | Defect fixes with before/after evidence | 2 | 3 | 6 | 3.3 | 0.67 |
| 9 | Use cases + 20 Playwright flows | 5 | 7 | 12 | 7.5 | 1.17 |
| 10 | Usability, accessibility, fix, before/after | 2 | 3 | 5 | 3.2 | 0.50 |
| 11 | Security: access matrix, ZAP, pip-audit | 2 | 3 | 5 | 3.2 | 0.50 |
| 12 | Performance + recovery tests | 2 | 4 | 7 | 4.2 | 0.83 |
| 13 | Mutation testing + custom operators + analysis | 3 | 5 | 9 | 5.3 | 1.00 |
| 14 | CI gate + fixed and blocked pull requests | 2 | 3 | 6 | 3.3 | 0.67 |
| 15 | Defect log, issues, RCA, Pareto, reports, final report | 4 | 6 | 10 | 6.3 | 1.00 |
| | **Total** | **40.5** | **62.5** | **110** | **66.8** | **σ_total = √Σσ² = √9.78 = 3.13** |

Planned effort with about 95 % confidence: 66.8 ± 2σ = **60.5 to 73.0 person-hours**,
about 33 hours per member for a team of two. Actual effort is reported in
[PROGRESS_REPORTS.md](PROGRESS_REPORTS.md).

## 6. Risk register

Likelihood (L) and impact (I) on a 1–5 scale; score = L × I.
**High ≥ 15, Medium 8–14, Low ≤ 7.**

### 6.1 Product risks

| ID | Risk | L | I | Score | Mitigation (tests) | Outcome |
|---|---|---|---|---|---|---|
| PR-1 | A write path changes status against the flow (BR-3) | 4 | 5 | **20 High** | State-transition tests on every path (API follow-up, PATCH, staff form, Kanban, public view) | Occurred: DEF-01, 02, 06, 10 (3 fixed) |
| PR-2 | A ticket is resolved while dependencies are open (BR-2) | 4 | 4 | **16 High** | Decision table, MCC/MC-DC, dependency tests per path | Occurred: DEF-01, 06, 10 |
| PR-3 | Users reach data or actions outside their role (BR-4) | 3 | 5 | **15 High** | Access matrix, API permission tests | Occurred (minor): DEF-09 |
| PR-4 | Invalid input accepted or crashes the server (BR-1) | 3 | 3 | 9 Medium | Generated EP/BVA cases | Occurred: DEF-03, 04, 05, 14 |
| PR-5 | A failed write leaves inconsistent data | 2 | 5 | 10 Medium | Fault-injection recovery test | Occurred: DEF-13 |
| PR-6 | Response times too slow under concurrent use | 3 | 3 | 9 Medium | k6 at 1 and 5 users with p95 targets | Occurred: DEF-16 |
| PR-7 | W1 screens unusable with keyboard / screen reader | 3 | 3 | 9 Medium | axe, Lighthouse, keyboard task | Occurred: DEF-15 (fixed) |
| PR-8 | Known-vulnerable dependency or missing security headers | 2 | 4 | 8 Medium | pip-audit, ZAP | Occurred: test-only advisory (fixed), DEF-11 |

### 6.2 Project risks

| ID | Risk | L | I | Score | Mitigation | Outcome |
|---|---|---|---|---|---|---|
| PJ-1 | Tool environment fails (Windows blocks native wheels, Docker unavailable, disk full) | 4 | 4 | **16 High** | Run everything in WSL; tools installed natively (SonarQube, ZAP, k6) without Docker | Occurred twice; mitigated, about 2 h lost |
| PJ-2 | Not enough time to finish every activity | 3 | 4 | 12 Medium | Three-point plan, scripted and repeatable runs, CI does the reruns | Controlled |

### 6.3 5 × 5 risk matrix (initial assessment)

| Likelihood ↓ / Impact → | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| **5** | | | | | |
| **4** | | | | PR-2, PJ-1 | PR-1 |
| **3** | | | PR-4, PR-6, PR-7 | PJ-2 | PR-3 |
| **2** | | | | PR-8 | PR-5 |
| **1** | | | | | |

Risk-based priority: PR-1, PR-2 and PR-3 got the most tests (state
transitions, decision table, MCC/MC-DC, access matrix) and the critical
module for MCC/MC-DC.

## 7. Entry criteria

- Baseline builds and the upstream suite passes (570 tests) on the test environment.
- Demo data seeds reproducibly (141 tickets, fixed seed).
- Requirements and business rules reviewed (SCOPE.md).

## 8. Exit criteria

| # | Criterion | Target |
|---|---|---|
| EC-1 | Critical module (`ticket_rules.py`) statement and branch coverage | 100 % |
| EC-2 | MCC and MC/DC for BR-2 complete | all feasible rows / independence pairs |
| EC-3 | Mutation score on the critical module | ≥ 90 %; every surviving mutant analysed |
| EC-4 | Every FR/BR traced to at least one passing or defect-pinning test | 100 % |
| EC-5 | Planned tests executed | 100 %; pass rate of non-defect tests 100 % |
| EC-6 | Open defects of severity Critical | 0 |
| EC-7 | Open defects of severity High on W1/W2 main paths | 0 (or accepted with a workaround by the product owner) |
| EC-8 | Upstream regression suite | 100 % pass |
| EC-9 | Performance: p95 read < 500 ms, write < 1500 ms, errors < 1 % at 1 and 5 users | all four runs |
| EC-10 | Accessibility: fixed screen without critical/serious axe violations; keyboard task passes | yes |
| EC-11 | Security: 0 High ZAP alerts; 0 known-vulnerable dependencies | yes |
| EC-12 | Every new write path has a negative test that sends a disallowed status directly (from RCA-1) | yes |

**Suspension:** environment unavailable, or a Critical defect blocks a
workflow. **Resumption:** environment restored and smoke test (UC-1 main,
UC-3 main) passes.

## 9. Deliverables

Test plan (this document), scope, traceability matrix, test code, evidence
(`docs/team/evidence/`), defect log and GitHub Issues, RCA, Pareto chart,
progress reports with GQM metrics, test completion report, CI workflow and
pull requests, AI use record, final report (PDF).
