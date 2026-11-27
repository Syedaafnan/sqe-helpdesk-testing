#!/usr/bin/env bash
# Creates the defect labels and one GitHub Issue per defect in the team repo.
# usage: bash docs/team/issues/create_issues.sh   (needs: gh auth login)
set -euo pipefail
cd "$(dirname "$0")"
REPO=Syedaafnan/sqe-helpdesk-testing
gh label create defect --color d73a4a --repo "$REPO" --force
gh label create severity:high --color b60205 --repo "$REPO" --force
gh label create severity:medium --color fbca04 --repo "$REPO" --force
gh label create severity:low --color 0e8a16 --repo "$REPO" --force
gh label create status:fixed --color 1d76db --repo "$REPO" --force
gh label create priority:P1 --color 5319e7 --repo "$REPO" --force
gh label create priority:P2 --color 8a63d2 --repo "$REPO" --force
gh label create priority:P3 --color c5b4e3 --repo "$REPO" --force
gh label create priority:P4 --color ededed --repo "$REPO" --force
url=$(gh issue create --repo "$REPO" --title "[DEF-01] Follow-up API changes ticket status without checking the status flow or open dependencies" --label "defect,severity:high,status:fixed,priority:P1" --body-file DEF-01.md)
echo "$url"
gh issue close "$url" --comment "Fixed: see the Defect Log in docs/team/SE3002_Final_Report.docx and the before/after evidence."
url=$(gh issue create --repo "$REPO" --title "[DEF-02] PATCH /api/tickets/{id}/ changes status without the status flow" --label "defect,severity:high,status:fixed,priority:P1" --body-file DEF-02.md)
echo "$url"
gh issue close "$url" --comment "Fixed: see the Defect Log in docs/team/SE3002_Final_Report.docx and the before/after evidence."
url=$(gh issue create --repo "$REPO" --title "[DEF-03] POST /api/tickets/ without description returns HTTP 500" --label "defect,severity:medium,priority:P2" --body-file DEF-03.md)
echo "$url"
url=$(gh issue create --repo "$REPO" --title "[DEF-04] Missing or blank description is reported on field 'body', not 'description'" --label "defect,severity:low,priority:P3" --body-file DEF-04.md)
echo "$url"
url=$(gh issue create --repo "$REPO" --title "[DEF-05] Omitting priority on ticket creation is rejected although the default is 3" --label "defect,severity:low,priority:P3" --body-file DEF-05.md)
echo "$url"
url=$(gh issue create --repo "$REPO" --title "[DEF-06] Kanban endpoint writes status without flow, dependency check or history record" --label "defect,severity:high,priority:P1" --body-file DEF-06.md)
echo "$url"
url=$(gh issue create --repo "$REPO" --title "[DEF-07] Repeating an identical follow-up POST creates a duplicate record" --label "defect,severity:low,priority:P3" --body-file DEF-07.md)
echo "$url"
url=$(gh issue create --repo "$REPO" --title "[DEF-08] page_size has no upper bound on the ticket API" --label "defect,severity:medium,priority:P2" --body-file DEF-08.md)
echo "$url"
url=$(gh issue create --repo "$REPO" --title "[DEF-09] /system_settings/ is reachable by non-staff users" --label "defect,severity:low,priority:P3" --body-file DEF-09.md)
echo "$url"
url=$(gh issue create --repo "$REPO" --title "[DEF-10] Staff ticket form enforces status flow and dependencies only in the browser" --label "defect,severity:high,status:fixed,priority:P1" --body-file DEF-10.md)
echo "$url"
gh issue close "$url" --comment "Fixed: see the Defect Log in docs/team/SE3002_Final_Report.docx and the before/after evidence."
url=$(gh issue create --repo "$REPO" --title "[DEF-11] No Content-Security-Policy header" --label "defect,severity:medium,priority:P2" --body-file DEF-11.md)
echo "$url"
url=$(gh issue create --repo "$REPO" --title "[DEF-12] Ticket secret key and e-mail address are sent in the URL query" --label "defect,severity:low,priority:P4" --body-file DEF-12.md)
echo "$url"
url=$(gh issue create --repo "$REPO" --title "[DEF-13] Status change is not atomic: a failed follow-up write leaves the new status saved" --label "defect,severity:high,priority:P1" --body-file DEF-13.md)
echo "$url"
url=$(gh issue create --repo "$REPO" --title "[DEF-14] Crafted public=on value on the staff update form causes HTTP 500" --label "defect,severity:low,priority:P3" --body-file DEF-14.md)
echo "$url"
url=$(gh issue create --repo "$REPO" --title "[DEF-15] Ticket lookup form inputs have no accessible name; navbar list contains a div" --label "defect,severity:medium,status:fixed,priority:P2" --body-file DEF-15.md)
echo "$url"
gh issue close "$url" --comment "Fixed: see the Defect Log in docs/team/SE3002_Final_Report.docx and the before/after evidence."
url=$(gh issue create --repo "$REPO" --title "[DEF-16] Ticket API loads custom fields for every accessible ticket on each request (N+1 queries)" --label "defect,severity:high,priority:P1" --body-file DEF-16.md)
echo "$url"
