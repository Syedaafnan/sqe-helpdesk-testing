**Severity:** High  
**Priority:** P1  
**Triage decision:** Accept, must fix before release: inconsistent shared record after a failure (blocks release).  
**Area:** W2, FR-10, reliability  
**Status:** Open

### Environment
django-helpdesk baseline 7bf832c (Django 6.1.3, DRF 3.18.3), demo site seeded with `demo_data` (seed 1476), Python 3.12 on Ubuntu 24.04 (WSL2).

### Steps to reproduce
1. Resolve a ticket through `POST /api/followups/` while the FollowUp INSERT fails once (e.g. `database is locked`).
2. Retry the same request.

### Expected
Step 1: 500 and the ticket stays Open. Step 2: 201, status Resolved, one FollowUp recording the change.

### Actual
Step 1: 500 but the ticket is already Resolved with no FollowUp. Step 2: the retry sees no status change, so the history never records it.

### Automated test
`tests/team/api/test_recovery.py::test_rec02`, `test_rec03` (xfail strict)

### Evidence
pytest output

### Notes
Suggested fix: wrap `update_ticket()` in `transaction.atomic()` (or enable `ATOMIC_REQUESTS`).

Defect log: final report (docs/team/SE3002_Final_Report.docx), DEF-13
