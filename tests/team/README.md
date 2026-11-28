# Team Tests

Everything in this folder is written by our team. Upstream tests in `tests/`
earn no marks and aren't changed.

| Folder | Test level | Owner area | Tool |
|---|---|---|---|
| `unit/` | White-box unit tests (100% statement + branch, MCC, MC/DC) | Area 1 | pytest, coverage.py |
| `api/` | API and integration tests (EP, 3-point BVA, decision table, state transition) | Area 2 | pytest, Django test client / Requests |
| `datagen/` | OpenAPI spec and test data generator | Area 2 | Python, PyYAML |
| `e2e/` | Playwright use case, usability, keyboard and access-control tests | Area 3 | Playwright (Chromium), axe-core |
| `perf/` | k6 load scripts and recovery test | Area 3 | Grafana k6 OSS, pytest |
| `mutation/` | Custom mutation operators and surviving-mutant analysis | Area 1 | mutmut |
| `seed/` | Our test scenario: Butter & Bean, a gaming cafe in Islamabad | Shared | Python, Django ORM |

## Test scenario: Butter & Bean

The API and browser tests run against our own synthetic scenario, the support
desk of **Butter & Bean**, a gaming cafe in Islamabad with branches at F-7
Markaz and Blue Area (mascot: Biscuit, the cafe's golden retriever).

- Queues: Cafe Wi-Fi, Gaming Lounge, Ordering App, Kitchen and Equipment
- Staff: afnan (manager), arooj (tech lead), rayyan (barista), haider (lounge attendant, no user-management rights)
- Customers: baidar, naheed
- All data is fictional and lives in `seed/content.py`; e-mails use the reserved `.example` domain.

```bash
python manage.py demo_data --reset          # upstream demo data
python tests/team/seed/seed_butter_bean.py  # our scenario on top (safe to re-run)
```

The upstream demo accounts stay in place, so the k6 performance runs, which use
them, are unchanged.

## Baseline

- Upstream: https://github.com/django-helpdesk/django-helpdesk (BSD-3-Clause)
- Baseline commit: `7bf832c` (git tag `baseline`)
- Tested on Ubuntu 24.04 (WSL2), Python 3.12, Django 6.1.3, DRF 3.18.3, Node 22, Chromium (Playwright 1.55)

## Setup

```bash
python3.12 -m venv ~/venvs/helpdesk && source ~/venvs/helpdesk/bin/activate
pip install -e .
pip install -r tests/team/requirements.txt
python -m playwright install --with-deps chromium
npm install --no-package-lock && make static-vendor
python manage.py migrate
python manage.py loaddata emailtemplate.json demo.json
```

## Seed, start and reset

```bash
python manage.py demo_data --reset            # reset: same 141 demo tickets every time (seed 1476)
python tests/team/seed/seed_butter_bean.py    # our scenario on top
python manage.py runserver 0.0.0.0:8080       # http://localhost:8080, all test accounts use Pa33w0rd
```

## Run the tests

```bash
pytest -m "not e2e" --cov=src/helpdesk --cov=tests/team/datagen --cov-branch   # unit, API, recovery
pytest tests/team/e2e -m e2e                                                    # Playwright (site running)
bash tests/team/mutation/run_mutmut.sh 90                                       # mutation gate
bash tests/team/perf/run_k6.sh                                                  # k6 load runs (site running)
python tests/team/e2e/lighthouse_screens.py                                     # Lighthouse, 4 key screens
```

CI runs the same steps on every pull request: `.github/workflows/quality-gate.yml`.
Full details and results: the final report (submitted as PDF).
