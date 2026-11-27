"""EP and 3-point BVA on every API input, driven by the generator output.

Each generated case changes ONE field of an otherwise valid request.
Valid -> 2xx and the shared Ticket record is read back.
Invalid -> 400 and the shared record is unchanged.
"""

import pytest

from helpdesk.models import Ticket
from tests.team.seed import content as cafe

from .conftest import followup_count, load_cases, start_state_for

pytestmark = [pytest.mark.api, pytest.mark.django_db]

# Open defects found by these generated cases (see final report, Defect Log).
# strict=True: if a defect is fixed the test XPASSes and fails, so the marker
# must be removed - the known-defect list cannot silently go stale.
KNOWN_DEFECTS = {
    "createTicket.description.EP.missing_required": "DEF-03: missing description -> HTTP 500 (KeyError)",
    "createTicket.description.EP.null": "DEF-04: error reported on 'body', not 'description'",
    "createTicket.description.BVA.minLength-1": "DEF-04: error reported on 'body', not 'description'",
    "createTicket.priority.EP.omitted_optional": "DEF-05: priority has model default 3 but API requires it",
}


def mark_known(cases):
    return [
        pytest.param(c, marks=pytest.mark.xfail(strict=True, reason=KNOWN_DEFECTS[c["id"]]))
        if c["id"] in KNOWN_DEFECTS
        else c
        for c in cases
    ]


def apply_case(payload, case, ref):
    if case["omit"]:
        payload.pop(case["field"], None)
    else:
        payload[case["field"]] = ref if case["value"] == "{ref}" else case["value"]
    return payload


# ------------------------------------------------------------------ W1 create
@pytest.mark.parametrize("case", mark_known(load_cases("createTicket")), ids=lambda c: c["id"])
def test_create_ticket_inputs(case, staff_client, queue):
    payload = {
        "queue": queue.id,
        "title": "Ordering app stuck on the loading screen",
        "description": "Paper is stuck in tray 2.",
        "submitter_email": cafe.CUSTOMER_EMAIL,
        "priority": 3,
    }
    apply_case(payload, case, queue.id)
    before = Ticket.objects.count()

    response = staff_client.post("/api/tickets/", payload, format="json")

    if case["valid"]:
        assert response.status_code == 201, response.content
        # read back the shared record through the API
        read = staff_client.get(f"/api/tickets/{response.data['id']}/")
        assert read.status_code == 200
        assert read.data["status"] == Ticket.OPEN_STATUS  # FR-02
        if not case["omit"] and case["field"] != "queue":
            expected = case["value"]
            if case["field"] == "title":
                expected = expected.strip()
            assert read.data[case["field"]] == expected
        assert Ticket.objects.count() == before + 1
    else:
        assert response.status_code == 400, response.content
        assert case["field"] in response.data  # error names the field to correct
        assert Ticket.objects.count() == before


# ------------------------------------------------------------- W2 PATCH ticket
@pytest.mark.parametrize("case", load_cases("updateTicket"), ids=lambda c: c["id"])
def test_update_ticket_inputs(case, staff_client, make_ticket):
    start = start_state_for(case["value"]) if case["field"] == "status" and case["valid"] and not case["omit"] else Ticket.OPEN_STATUS
    ticket = make_ticket(status=start, priority=3)
    payload = apply_case({}, case, ticket.id)

    response = staff_client.patch(f"/api/tickets/{ticket.id}/", payload, format="json")
    ticket.refresh_from_db()

    if case["valid"]:
        assert response.status_code == 200, response.content
        if not case["omit"]:
            assert getattr(ticket, case["field"]) == case["value"]
    else:
        assert response.status_code == 400, response.content
        assert case["field"] in response.data
        assert (ticket.status, ticket.priority) == (start, 3)


# ---------------------------------------------------------- W2 add follow-up
@pytest.mark.parametrize("case", load_cases("createFollowUp"), ids=lambda c: c["id"])
def test_create_followup_inputs(case, staff_client, make_ticket):
    start = start_state_for(case["value"]) if case["field"] == "new_status" and case["valid"] and not case["omit"] else Ticket.OPEN_STATUS
    ticket = make_ticket(status=start)
    payload = {"ticket": ticket.id, "title": "Investigated", "comment": "Checked the tray.", "public": False}
    apply_case(payload, case, ticket.id)
    before = followup_count(ticket)

    response = staff_client.post("/api/followups/", payload, format="json")
    ticket.refresh_from_db()

    if case["valid"]:
        assert response.status_code == 201, response.content
        assert followup_count(ticket) == before + 1
        if case["field"] == "new_status" and not case["omit"]:
            assert ticket.status == case["value"]
    else:
        assert response.status_code == 400, response.content
        assert case["field"] in response.data
        assert followup_count(ticket) == before
        assert ticket.status == start
