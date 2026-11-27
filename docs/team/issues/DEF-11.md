**Severity:** Medium  
**Priority:** P2  
**Triage decision:** Defer to security hardening in next release: missing defence-in-depth header.  
**Area:** security  
**Status:** Open

### Environment
django-helpdesk baseline 7bf832c (Django 6.1.3, DRF 3.18.3), demo site seeded with `demo_data` (seed 1476), Python 3.12 on Ubuntu 24.04 (WSL2).

### Steps to reproduce
1. Request any page, e.g. `/` or `/tickets/submit/`, and inspect the response headers.

### Expected
A `Content-Security-Policy` header restricting script and style sources.

### Actual
No CSP header (ZAP rule 10038, 5 instances).

### Automated test
ZAP passive scan

### Evidence
`docs/team/evidence/security/zap_passive_report.html`

### Notes
Suggested fix: Django 6 `SECURE_CSP` setting with `ContentSecurityPolicyMiddleware`.

Defect log: final report (docs/team/SE3002_Final_Report.docx), DEF-11
