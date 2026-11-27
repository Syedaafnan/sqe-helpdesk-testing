**Severity:** Low  
**Priority:** P3  
**Triage decision:** Defer to backlog: duplicate comment only, no status corruption.  
**Area:** W2, repeated requests  
**Status:** Open

### Environment
django-helpdesk baseline 7bf832c (Django 6.1.3, DRF 3.18.3), demo site seeded with `demo_data` (seed 1476), Python 3.12 on Ubuntu 24.04 (WSL2).

### Steps to reproduce
1. Staff: send the same `POST /api/followups/` body twice (e.g. a network retry).

### Expected
The second identical request within a short window is recognised (idempotency key or duplicate check).

### Actual
Two identical FollowUp rows; the customer is e-mailed twice.

### Automated test
`test_crossflow_and_repeats.py::test_repeated_identical_followup_is_not_duplicated` (xfail strict)

### Evidence
pytest output

### Notes
Suggested fix: support an `Idempotency-Key` header or reject an identical follow-up within N seconds.

Defect log: final report (docs/team/SE3002_Final_Report.docx), DEF-07
