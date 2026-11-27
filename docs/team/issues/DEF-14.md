**Severity:** Low  
**Priority:** P3  
**Triage decision:** Defer to backlog: needs a crafted request, only staff can trigger it.  
**Area:** W2, robustness  
**Status:** Open

### Environment
django-helpdesk baseline 7bf832c (Django 6.1.3, DRF 3.18.3), demo site seeded with `demo_data` (seed 1476), Python 3.12 on Ubuntu 24.04 (WSL2).

### Steps to reproduce
1. Staff: POST to `/tickets/<id>/update/` with `public=on` (what a checkbox without `value` would send).

### Expected
The value is treated as true or rejected with a form error.

### Actual
HTTP 500: `ValidationError: "on" value must be either True or False.`

### Automated test
Found while writing `test_staff_form_rules.py`

### Evidence
traceback in pytest output

### Notes
Suggested fix: parse the field with a `forms.BooleanField`.

Defect log: final report (docs/team/SE3002_Final_Report.docx), DEF-14
