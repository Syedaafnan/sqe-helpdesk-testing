"""BR-3 state transition testing through the API (Workflow 2).

Every allowed change of state, and every disallowed change from each state,
is exercised on both write paths that change status:
  * POST  /api/followups/      (new_status)
  * PATCH /api/tickets/{id}/   (status)
After each request the shared Ticket record and its follow-ups are read back.
"""

import pytest

from .conftest import ALL_STATUSES, FLOW, followup_count

pytestmark = [pytest.mark.api, pytest.mark.django_db]

ALLOWED = [(s, t) for s in ALL_STATUSES for t in FLOW[s] if s != t]
DISALLOWED = [(s, t) for s in ALL_STATUSES for t in ALL_STATUSES if t not in FLOW[s] and s != t]
NAMES = {1: "Open", 2: "Reopened", 3: "Resolved", 4: "Closed", 5: "Duplicate"}


def tid(pair):
    return f"{NAMES[pair[0]]}->{NAMES[pair[1]]}"


def test_every_state_has_a_disallowed_change():
    """Coverage criterion: at least one disallowed change from each state."""
    assert {s for s, _ in DISALLOWED} == set(ALL_STATUSES)
    assert len(ALLOWED) == 10 and len(DISALLOWED) == 10


# ----------------------------------------------------------- follow-up path
@pytest.mark.parametrize("pair", ALLOWED, ids=tid)
def test_followup_allowed_transition(pair, staff_client, make_ticket):
    current, new = pair
    ticket = make_ticket(status=current)

    r = staff_client.post(
        "/api/followups/", {"ticket": ticket.id, "comment": "Moving on", "new_status": new}, format="json"
    )

    assert r.status_code == 201, r.content
    ticket.refresh_from_db()
    assert ticket.status == new
    last = ticket.followup_set.latest("date")
    assert last.new_status == new  # FR-10 history recorded
    assert NAMES[new] in last.title


@pytest.mark.parametrize("pair", DISALLOWED, ids=tid)
def test_followup_disallowed_transition_rejected(pair, staff_client, make_ticket):
    current, new = pair
    ticket = make_ticket(status=current)
    before = followup_count(ticket)

    r = staff_client.post(
        "/api/followups/", {"ticket": ticket.id, "comment": "Try", "new_status": new}, format="json"
    )

    assert r.status_code == 400, r.content
    assert "new_status" in r.data
    assert "cannot move" in str(r.data["new_status"])
    ticket.refresh_from_db()
    assert ticket.status == current  # rejected: shared record unchanged
    assert followup_count(ticket) == before


# ------------------------------------------------------------- PATCH path
@pytest.mark.parametrize("pair", ALLOWED, ids=tid)
def test_patch_allowed_transition(pair, staff_client, make_ticket):
    current, new = pair
    ticket = make_ticket(status=current)

    r = staff_client.patch(f"/api/tickets/{ticket.id}/", {"status": new}, format="json")

    assert r.status_code == 200, r.content
    assert staff_client.get(f"/api/tickets/{ticket.id}/").data["status"] == new


@pytest.mark.parametrize("pair", DISALLOWED, ids=tid)
def test_patch_disallowed_transition_rejected(pair, staff_client, make_ticket):
    current, new = pair
    ticket = make_ticket(status=current)

    r = staff_client.patch(f"/api/tickets/{ticket.id}/", {"status": new}, format="json")

    assert r.status_code == 400, r.content
    assert "status" in r.data
    assert staff_client.get(f"/api/tickets/{ticket.id}/").data["status"] == current


# -------------------------------------------- open dependencies (BR-2 / A1)
def test_followup_cannot_resolve_with_open_dependency(staff_client, make_ticket, add_open_dependency):
    ticket = make_ticket(status=1)
    add_open_dependency(ticket)

    r = staff_client.post(
        "/api/followups/", {"ticket": ticket.id, "comment": "Done", "new_status": 3}, format="json"
    )

    assert r.status_code == 400
    assert "resolve those first" in str(r.data["new_status"])
    ticket.refresh_from_db()
    assert ticket.status == 1


def test_followup_resolves_once_dependency_closed(staff_client, make_ticket, add_open_dependency):
    ticket = make_ticket(status=1)
    blocker = add_open_dependency(ticket)
    blocker.status = 4
    blocker.save()

    r = staff_client.post(
        "/api/followups/", {"ticket": ticket.id, "comment": "Done", "new_status": 3}, format="json"
    )

    assert r.status_code == 201
    ticket.refresh_from_db()
    assert ticket.status == 3


def test_comment_only_allowed_with_open_dependency(staff_client, make_ticket, add_open_dependency):
    ticket = make_ticket(status=1)
    add_open_dependency(ticket)

    r = staff_client.post("/api/followups/", {"ticket": ticket.id, "comment": "Waiting"}, format="json")

    assert r.status_code == 201
    ticket.refresh_from_db()
    assert ticket.status == 1
