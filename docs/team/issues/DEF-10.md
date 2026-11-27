**Severity:** High  
**Priority:** P1  
**Triage decision:** Fix now: rule bypass on the staff write path. Fixed through the DEF-10 pull request.  
**Area:** W2, BR-2, BR-3  
**Status:** Fixed (closed by the fix commit)

### Environment
django-helpdesk baseline 7bf832c (Django 6.1.3, DRF 3.18.3), demo site seeded with `demo_data` (seed 1476), Python 3.12 on Ubuntu 24.04 (WSL2).

### Steps to reproduce
1. Staff: open a ticket that depends on an open ticket; the Resolved radio is disabled.
2. Send the Respond form with `new_status=3` anyway (edited page or direct POST to `/tickets/<id>/update/`).
3. Same for a Closed ticket with `new_status=3`.

### Expected
The change is refused with a message; status unchanged; no follow-up saved.

### Actual
The ticket is resolved / moved Closed -> Resolved.

### Automated test
`tests/team/api/test_staff_form_rules.py` (posts the Respond form directly)

### Evidence
`evidence/api/def10_before_fix.txt` (2 failed), `def10_after_fix.txt` (4 passed)

### Notes
Fixed in `UpdateTicketView.form_valid` (fix pull request).

Defect log: final report (docs/team/SE3002_Final_Report.docx), DEF-10
