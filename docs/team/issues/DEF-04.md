**Severity:** Low  
**Priority:** P3  
**Triage decision:** Defer to backlog: wrong field name in the error, client can still recover.  
**Area:** W1, API  
**Status:** Open

### Environment
django-helpdesk baseline 7bf832c (Django 6.1.3, DRF 3.18.3), demo site seeded with `demo_data` (seed 1476), Python 3.12 on Ubuntu 24.04 (WSL2).

### Steps to reproduce
1. Staff: `POST /api/tickets/` with `description: null` or `""`.

### Expected
400 with the error under `description` (the field the client sent).

### Actual
400 with the error under `body` (the internal TicketForm field name).

### Automated test
`test_generated_inputs.py` cases `description.EP.null`, `description.BVA.minLength-1` (xfail strict)

### Evidence
pytest output

### Notes
Suggested fix: map `body` errors back to `description` in `TicketSerializer.create`.

Defect log: final report (docs/team/SE3002_Final_Report.docx), DEF-04
