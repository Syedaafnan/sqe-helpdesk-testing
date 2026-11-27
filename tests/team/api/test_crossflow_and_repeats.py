"""Cross-workflow integration (W1 output feeds W2), repeated requests and
endpoint weaknesses found while testing the API."""

import pytest

from helpdesk.models import FollowUp, Ticket, TicketChange
from tests.team.seed import content as cafe

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_w1_creates_ticket_that_w2_resolves_and_closes(staff_client, queue):
    # W1: submit
    r = staff_client.post(
        "/api/tickets/",
        {"queue": queue.id, "title": "Lounge Wi-Fi drops", "description": "Every 10 min during matches", "priority": 2},
        format="json",
    )
    assert r.status_code == 201
    tid = r.data["id"]
    assert staff_client.get(f"/api/tickets/{tid}/").data["status"] == 1

    # W2: resolve, then close, reading the shared record after each step
    for new in (3, 4):
        f = staff_client.post("/api/followups/", {"ticket": tid, "comment": "step", "new_status": new}, format="json")
        assert f.status_code == 201
        assert staff_client.get(f"/api/tickets/{tid}/").data["status"] == new

    # rejection after success: Closed -> Resolved is not allowed, state stays Closed
    bad = staff_client.post("/api/followups/", {"ticket": tid, "comment": "x", "new_status": 3}, format="json")
    assert bad.status_code == 400
    assert staff_client.get(f"/api/tickets/{tid}/").data["status"] == 4
    statuses = list(FollowUp.objects.filter(ticket_id=tid).order_by("id").values_list("new_status", flat=True))
    assert statuses == [None, 3, 4]  # opened, resolved, closed - nothing for the rejection


def test_status_filter_reads_w2_changes(staff_client, make_ticket):
    open_t, closed_t = make_ticket(status=1), make_ticket(status=4)
    r = staff_client.get("/api/tickets/?status=4")
    assert [t["id"] for t in r.data["results"]] == [closed_t.id]
    assert open_t.id not in [t["id"] for t in r.data["results"]]


def test_repeated_status_change_records_one_change(staff_client, make_ticket):
    """Repeating the same resolve request must not record a second status change."""
    ticket = make_ticket(status=1)
    body = {"ticket": ticket.id, "comment": "Fixed", "new_status": 3}

    first = staff_client.post("/api/followups/", body, format="json")
    second = staff_client.post("/api/followups/", body, format="json")

    assert first.status_code == 201 and second.status_code == 201
    ticket.refresh_from_db()
    assert ticket.status == 3
    assert FollowUp.objects.filter(ticket=ticket, new_status=3).count() == 1
    assert TicketChange.objects.filter(followup__ticket=ticket, field="Status").count() == 1


@pytest.mark.xfail(strict=True, reason="DEF-07: identical follow-up POST creates a duplicate record")
def test_repeated_identical_followup_is_not_duplicated(staff_client, make_ticket):
    ticket = make_ticket(status=1)
    body = {"ticket": ticket.id, "comment": "Same text", "new_status": 3}
    staff_client.post("/api/followups/", body, format="json")
    staff_client.post("/api/followups/", body, format="json")
    assert FollowUp.objects.filter(ticket=ticket, comment="Same text").count() == 1


@pytest.mark.xfail(strict=True, reason="DEF-08: page_size has no upper bound")
def test_page_size_is_capped(staff_client, queue):
    Ticket.objects.bulk_create(
        [Ticket(queue=queue, title=f"T{i}", submitter_email=cafe.SECOND_CUSTOMER_EMAIL) for i in range(120)]
    )
    r = staff_client.get("/api/tickets/?page_size=100000")
    assert r.status_code == 200
    assert len(r.data["results"]) <= 100  # a client can request every row in one response


def test_unknown_status_filter_is_ignored(staff_client, make_ticket):
    """Weakness (documented, low): ?status=abc silently returns every ticket."""
    make_ticket(status=1)
    make_ticket(status=4)
    r = staff_client.get("/api/tickets/?status=abc")
    assert r.status_code == 200
    assert r.data["count"] == 2


def test_cannot_create_ticket_in_unknown_queue(staff_client):
    before = Ticket.objects.count()
    r = staff_client.post(
        "/api/tickets/", {"queue": 999, "title": "T", "description": "D", "priority": 3}, format="json"
    )
    assert r.status_code == 400
    assert Ticket.objects.count() == before
