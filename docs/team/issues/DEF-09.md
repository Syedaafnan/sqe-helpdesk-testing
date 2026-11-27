**Severity:** Low  
**Priority:** P3  
**Triage decision:** Defer to backlog: settings page is read-only for non-staff, low exposure.  
**Area:** security, BR-4  
**Status:** Open

### Environment
django-helpdesk baseline 7bf832c (Django 6.1.3, DRF 3.18.3), demo site seeded with `demo_data` (seed 1476), Python 3.12 on Ubuntu 24.04 (WSL2).

### Steps to reproduce
1. Log in as a customer (non-staff).
2. Open `/system_settings/`.

### Expected
Redirect to login or 403, as for the other staff pages.

### Actual
200 with the 'System Settings' maintenance menu (the linked pages themselves are protected).

### Automated test
`tests/team/e2e/test_security_access.py::test_ac09_customer_does_not_see_system_settings` (xfail strict)

### Evidence
screenshot `docs/team/evidence/e2e/test_ac09_*.png`

### Notes
Suggested fix: wrap the view with `helpdesk_superuser_required` instead of `login_required`.

Defect log: final report (docs/team/SE3002_Final_Report.docx), DEF-09
