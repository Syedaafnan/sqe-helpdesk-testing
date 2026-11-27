**Severity:** Medium  
**Priority:** P2  
**Triage decision:** Accept, fix in next release: server error on a common input mistake, no data loss.  
**Area:** W1, API  
**Status:** Open

### Environment
django-helpdesk baseline 7bf832c (Django 6.1.3, DRF 3.18.3), demo site seeded with `demo_data` (seed 1476), Python 3.12 on Ubuntu 24.04 (WSL2).

### Steps to reproduce
1. Staff: `POST /api/tickets/` with `{"queue": 1, "title": "T", "priority": 3}` (no description).

### Expected
400 with `{"description": ["This field is required."]}`.

### Actual
HTTP 500 (KeyError on `description` in `TicketSerializer.create`).

### Automated test
`test_generated_inputs.py` case `createTicket.description.EP.missing_required` (xfail strict)

### Evidence
generated case list `tests/team/datagen/generated/cases.json`

### Notes
Suggested fix: mark `description` required in the serializer (or use `.get`).

Defect log: final report (docs/team/SE3002_Final_Report.docx), DEF-03
