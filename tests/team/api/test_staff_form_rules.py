"""DEF-10: the staff ticket form must enforce BR-2/BR-3 on the server.

The staff page only disables or hides the status radios that are not
allowed. A request sent without the page (or with the page edited) used to be
saved as-is. These tests post the form the way the Respond tab does.
"""

import pytest
from django.test import Client

from helpdesk.models import FollowUp, Ticket

pytestmark = [pytest.mark.api, pytest.mark.django_db]


@pytest.fixture
def web(staff_user):
    c = Client()
    c.force_login(staff_user)
    return c


def post_update(web, ticket, new_status, comment="update"):
    return web.post(
        f"/tickets/{ticket.id}/update/",
        {
            "comment": comment,
            "new_status": str(new_status),
            "title": ticket.title,
            "queue": str(ticket.queue_id),
            "priority": str(ticket.priority),
            "owner": "0",
            "public": "1",  # what the page checkbox sends
        },
        follow=True,
    )


def test_staff_form_control_allowed_change_is_saved(web, make_ticket):
    """Control: the same request with an allowed change does change the status."""
    ticket = make_ticket(status=Ticket.OPEN_STATUS)
    post_update(web, ticket, Ticket.RESOLVED_STATUS, "Fixed")
    ticket.refresh_from_db()
    assert ticket.status == Ticket.RESOLVED_STATUS


def test_staff_form_rejects_resolve_with_open_dependency(web, make_ticket, add_open_dependency):
    ticket = make_ticket(status=Ticket.OPEN_STATUS)
    add_open_dependency(ticket)
    r = post_update(web, ticket, Ticket.RESOLVED_STATUS, "forced")
    ticket.refresh_from_db()
    assert ticket.status == Ticket.OPEN_STATUS
    assert not FollowUp.objects.filter(ticket=ticket, comment="forced").exists()
    assert "depends on tickets that are still open" in r.content.decode()


def test_staff_form_rejects_closed_to_resolved(web, make_ticket):
    ticket = make_ticket(status=Ticket.CLOSED_STATUS)
    r = post_update(web, ticket, Ticket.RESOLVED_STATUS, "forced")
    ticket.refresh_from_db()
    assert ticket.status == Ticket.CLOSED_STATUS
    assert "cannot move from status 4 to 3" in r.content.decode()


def test_staff_form_comment_allowed_with_open_dependency(web, make_ticket, add_open_dependency):
    """BR-2 row R2: keeping the status (comment only) is still allowed."""
    ticket = make_ticket(status=Ticket.OPEN_STATUS)
    add_open_dependency(ticket)
    post_update(web, ticket, Ticket.OPEN_STATUS, "just a note")
    assert FollowUp.objects.filter(ticket=ticket, comment="just a note").exists()
