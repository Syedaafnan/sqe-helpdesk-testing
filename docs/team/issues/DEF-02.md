**Severity:** High  
**Priority:** P1  
**Triage decision:** Fix now: rule bypass on a main write path. Fixed and verified (before/after evidence).  
**Area:** W2, BR-3  
**Status:** Fixed (closed by the fix commit)

### Environment
django-helpdesk baseline 7bf832c (Django 6.1.3, DRF 3.18.3), demo site seeded with `demo_data` (seed 1476), Python 3.12 on Ubuntu 24.04 (WSL2).

### Steps to reproduce
1. Staff: create a ticket and close it.
2. `PATCH /api/tickets/<id>/` with `{"status": 3}`.

### Expected
400; status stays Closed.

### Actual
200; status becomes Resolved.

### Automated test
`test_state_transitions.py::test_patch_disallowed_transition_rejected`

### Evidence
`evidence/api/before_fix_baseline.txt`, `after_fix.txt`

### Notes
Fixed in `TicketSerializer.validate`.

Defect log: final report (docs/team/SE3002_Final_Report.docx), DEF-02
