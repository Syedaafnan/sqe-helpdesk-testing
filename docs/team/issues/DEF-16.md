**Severity:** High  
**Priority:** P1  
**Triage decision:** Accept, must fix before release: p95 targets missed under 5 users (blocks release).  
**Area:** API, performance  
**Status:** Open

### Environment
django-helpdesk baseline 7bf832c (Django 6.1.3, DRF 3.18.3), demo site seeded with `demo_data` (seed 1476), Python 3.12 on Ubuntu 24.04 (WSL2).

### Steps to reproduce
1. Seed the demo data and create about 300 tickets.
2. `GET /api/tickets/<id>/` as staff and count the SQL queries (or time it).

### Expected
A detail request runs a handful of queries; a list request scales with the page size, not with the whole table.

### Actual
1289 SQL queries and 2.65 s to return one ticket with 322 tickets in the database; time grows linearly with the ticket count.

### Automated test
k6 per-endpoint breakdown (`tests/team/perf/helpdesk_load.js`)

### Evidence
`docs/team/evidence/performance/diagnosis.txt`, k6 summaries

### Notes
Cause: `TicketViewSet.get_queryset()` (and `UserTicketViewSet`) call `set_custom_field_values()` on every ticket before filtering or paginating. Suggested fix: call it only on the object(s) being serialised.

Defect log: final report (docs/team/SE3002_Final_Report.docx), DEF-16
