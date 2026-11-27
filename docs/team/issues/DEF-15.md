**Severity:** Medium  
**Priority:** P2  
**Triage decision:** Fix now: accessibility barrier on the W1 lookup screen. Fixed and verified (Lighthouse 91 to 100).  
**Area:** accessibility  
**Status:** Fixed (closed by the fix commit)

### Environment
django-helpdesk baseline 7bf832c (Django 6.1.3, DRF 3.18.3), demo site seeded with `demo_data` (seed 1476), Python 3.12 on Ubuntu 24.04 (WSL2).

### Steps to reproduce
1. Open `/view/` and run axe-core or Lighthouse.

### Expected
Every input has an accessible name; lists contain only `li`.

### Actual
axe `label` (critical, 2 inputs) and `list` (serious); Lighthouse accessibility 91.

### Automated test
`tests/team/e2e/test_accessibility.py::test_ax1_*`

### Evidence
`evidence/accessibility/axe_view_lookup_before.json`, Lighthouse before/after reports

### Notes
Fixed: `id` on the two inputs (the labels already used `for=`), `li` instead of `div` in the navbar. Lighthouse 100.

Defect log: final report (docs/team/SE3002_Final_Report.docx), DEF-15
