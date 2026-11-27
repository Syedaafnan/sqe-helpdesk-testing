**Severity:** Medium  
**Priority:** P2  
**Triage decision:** Accept, fix in next release: unbounded page size enables slow responses.  
**Area:** API, performance  
**Status:** Open

### Environment
django-helpdesk baseline 7bf832c (Django 6.1.3, DRF 3.18.3), demo site seeded with `demo_data` (seed 1476), Python 3.12 on Ubuntu 24.04 (WSL2).

### Steps to reproduce
1. Staff: `GET /api/tickets/?page_size=100000` with more than 100 tickets.

### Expected
Page size capped (e.g. `max_page_size = 100`).

### Actual
Every ticket is returned in one response (with a custom-field query per ticket).

### Automated test
`test_crossflow_and_repeats.py::test_page_size_is_capped` (xfail strict)

### Evidence
pytest output

### Notes
Suggested fix: `max_page_size = 100` on `ConservativePagination`.

Defect log: final report (docs/team/SE3002_Final_Report.docx), DEF-08
