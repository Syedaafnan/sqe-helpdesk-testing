**Severity:** High  
**Priority:** P1  
**Triage decision:** Fix now: rule bypass on a main write path. Fixed and verified (before/after evidence).  
**Area:** W2, BR-3, BR-2  
**Status:** Fixed (closed by the fix commit)

### Environment
django-helpdesk baseline 7bf832c (Django 6.1.3, DRF 3.18.3), demo site seeded with `demo_data` (seed 1476), Python 3.12 on Ubuntu 24.04 (WSL2).

### Steps to reproduce
1. As a staff user, create a ticket and close it (status 4).
2. `POST /api/followups/` with `{"ticket": <id>, "comment": "x", "new_status": 3}`.
3. Repeat on an Open ticket that depends on another Open ticket.

### Expected
400 with a message naming the allowed statuses; for the dependent ticket, 400 saying the dependencies must be resolved first. Status unchanged.

### Actual
201; the ticket moves Closed -> Resolved, and the dependent ticket is resolved although its dependency is open.

### Automated test
`tests/team/api/test_state_transitions.py` (10 disallowed transitions + dependency cases)

### Evidence
`docs/team/evidence/api/before_fix_baseline.txt` (24 failures), `after_fix.txt`

### Notes
Fixed in `src/helpdesk/serializers.py` (`enforce_status_rules`, using `helpdesk/ticket_rules.py`).

Defect log: final report (docs/team/SE3002_Final_Report.docx), DEF-01
