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

Setup: see [docs/team/BASELINE.md](../../docs/team/BASELINE.md).
