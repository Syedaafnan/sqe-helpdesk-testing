**Severity:** Low  
**Priority:** P4  
**Triage decision:** Won't fix now: upstream design of the ticket link; risk documented and accepted.  
**Area:** security, privacy  
**Status:** Open

### Environment
django-helpdesk baseline 7bf832c (Django 6.1.3, DRF 3.18.3), demo site seeded with `demo_data` (seed 1476), Python 3.12 on Ubuntu 24.04 (WSL2).

### Steps to reproduce
1. Submit a ticket on the public form; note the redirect URL `/view/?ticket=..&email=..&key=..`.

### Expected
Secrets not in the URL (they end up in server logs, browser history and Referer headers).

### Actual
E-mail and secret key in the query string (ZAP rule 10024).

### Automated test
ZAP passive scan

### Evidence
`zap_passive_report.html`

### Notes
Design decision upstream; suggested: POST-based lookup or a signed short-lived token.

Defect log: final report (docs/team/SE3002_Final_Report.docx), DEF-12
