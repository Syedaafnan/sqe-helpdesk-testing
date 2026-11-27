**Severity:** Low  
**Priority:** P3  
**Triage decision:** Defer to backlog: API contract mismatch with a simple workaround (send priority).  
**Area:** W1, FR-03  
**Status:** Open

### Environment
django-helpdesk baseline 7bf832c (Django 6.1.3, DRF 3.18.3), demo site seeded with `demo_data` (seed 1476), Python 3.12 on Ubuntu 24.04 (WSL2).

### Steps to reproduce
1. Staff: `POST /api/tickets/` with queue, title, description and no `priority`.

### Expected
201 and priority 3 (model default, FR-03).

### Actual
400 `priority: This field is required.`

### Automated test
`test_generated_inputs.py` case `priority.EP.omitted_optional` (xfail strict)

### Evidence
pytest output

### Notes
Suggested fix: `required=False, default=3` on the serializer field.

Defect log: final report (docs/team/SE3002_Final_Report.docx), DEF-05
