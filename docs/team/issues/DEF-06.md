**Severity:** High  
**Priority:** P1  
**Triage decision:** Accept, must fix before release: bypasses BR-2/BR-3 and loses history (blocks release).  
**Area:** W2, BR-2, BR-3, FR-10  
**Status:** Open

### Environment
django-helpdesk baseline 7bf832c (Django 6.1.3, DRF 3.18.3), demo site seeded with `demo_data` (seed 1476), Python 3.12 on Ubuntu 24.04 (WSL2).

### Steps to reproduce
1. Staff: close a ticket.
2. `POST /tickets/<id>/kanban-update/` with JSON `{"status": 3}`.
3. Repeat on a ticket with an open dependency; check the follow-ups.

### Expected
Disallowed moves rejected with 400; a FollowUp records every accepted change.

### Actual
200; status changes in every case and no FollowUp is written.

### Automated test
`tests/team/api/test_kanban_def06.py` (3 xfail strict + control)

### Evidence
pytest output

### Notes
Suggested fix: call `ticket_rules.check_status_change` and `update_ticket(...)` instead of `ticket.save()`.

Defect log: final report (docs/team/SE3002_Final_Report.docx), DEF-06
