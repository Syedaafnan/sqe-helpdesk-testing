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

Setup: see Appendix A of the final report (docs/team/SE3002_Final_Report.docx).
