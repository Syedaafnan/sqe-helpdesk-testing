"""BR-4 role-based access on the API endpoints used by both workflows."""

import pytest

from helpdesk.models import Ticket
from tests.team.seed import content as cafe

pytestmark = [pytest.mark.api, pytest.mark.django_db]

ENDPOINTS = [
    ("get", "/api/tickets/"),
    ("post", "/api/tickets/"),
    ("post", "/api/followups/"),
]


@pytest.mark.parametrize("method, url", ENDPOINTS)
def test_anonymous_denied(method, url, anon_client):
    r = getattr(anon_client, method)(url, {}, format="json")
    assert r.status_code in (401, 403)


@pytest.mark.parametrize("method, url", ENDPOINTS)
def test_non_staff_denied(method, url, submitter_client):
    r = getattr(submitter_client, method)(url, {}, format="json")
    assert r.status_code == 403


def test_staff_allowed_to_list(staff_client, make_ticket):
    make_ticket()
    r = staff_client.get("/api/tickets/")
    assert r.status_code == 200
    assert r.data["count"] == 1


def test_inactive_staff_denied(staff_user, staff_client):
    """BR-4 condition is_active. force_authenticate skips the login backend,
    so this checks the permission class itself (defence in depth)."""
    staff_user.is_active = False
    staff_user.save()
    assert staff_client.get("/api/tickets/").status_code == 403


def test_non_staff_cannot_change_status(submitter_client, make_ticket):
    ticket = make_ticket(status=1)
    r = submitter_client.patch(f"/api/tickets/{ticket.id}/", {"status": 3}, format="json")
    assert r.status_code == 403
    ticket.refresh_from_db()
    assert ticket.status == 1


def test_user_tickets_only_own(submitter_client, make_ticket):
    mine = make_ticket(email=cafe.CUSTOMER_EMAIL, title="My latte order")
    make_ticket(email=cafe.SECOND_CUSTOMER_EMAIL, title="Naheed's app issue")
    r = submitter_client.get("/api/user_tickets/")
    assert r.status_code == 200
    assert [t["id"] for t in r.data["results"]] == [mine.id]


def test_user_without_email_sees_nothing(submitter_user, submitter_client, make_ticket):
    submitter_user.email = ""
    submitter_user.save()
    make_ticket(email="")
    r = submitter_client.get("/api/user_tickets/")
    assert r.data["count"] == 0


def test_status_forced_open_on_create(staff_client, queue):
    """FR-02 / assumption A2: a client-sent status is ignored on creation."""
    r = staff_client.post(
        "/api/tickets/",
        {"queue": queue.id, "title": "T", "description": "D", "priority": 3, "status": 4},
        format="json",
    )
    assert r.status_code == 201
    assert Ticket.objects.get(id=r.data["id"]).status == 1
