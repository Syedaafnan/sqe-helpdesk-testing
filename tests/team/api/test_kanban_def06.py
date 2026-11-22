"""DEF-06: the Kanban drag-and-drop endpoint writes the status directly.

POST /tickets/<id>/kanban-update/ {"status": n} only checks that n is a valid
status code. It does not apply the status flow (BR-3), the open-dependency
rule (BR-2) or record the change in the ticket history (FR-10).
"""

import json

import pytest
from django.test import Client

from helpdesk.models import FollowUp, Ticket

pytestmark = [pytest.mark.api, pytest.mark.django_db]


@pytest.fixture
def web(staff_user):
    c = Client()
    c.force_login(staff_user)
    return c


def drag(web, ticket, status):
    return web.post(
        f"/tickets/{ticket.id}/kanban-update/",
        json.dumps({"status": status}),
        content_type="application/json",
    )


def test_kanban_control_allowed_move_and_invalid_code(web, make_ticket):
    ticket = make_ticket(status=Ticket.OPEN_STATUS)
    assert drag(web, ticket, Ticket.RESOLVED_STATUS).status_code == 200
    ticket.refresh_from_db()
    assert ticket.status == Ticket.RESOLVED_STATUS
    assert drag(web, ticket, 99).status_code == 400  # the one check it does make


@pytest.mark.xfail(strict=True, reason="DEF-06: kanban ignores the status flow")
def test_kanban_rejects_closed_to_resolved(web, make_ticket):
    ticket = make_ticket(status=Ticket.CLOSED_STATUS)
    drag(web, ticket, Ticket.RESOLVED_STATUS)
    ticket.refresh_from_db()
    assert ticket.status == Ticket.CLOSED_STATUS


@pytest.mark.xfail(strict=True, reason="DEF-06: kanban ignores open dependencies")
def test_kanban_rejects_resolve_with_open_dependency(web, make_ticket, add_open_dependency):
    ticket = make_ticket(status=Ticket.OPEN_STATUS)
    add_open_dependency(ticket)
    drag(web, ticket, Ticket.RESOLVED_STATUS)
    ticket.refresh_from_db()
    assert ticket.status == Ticket.OPEN_STATUS


@pytest.mark.xfail(strict=True, reason="DEF-06: kanban status change leaves no history record (FR-10)")
def test_kanban_move_is_recorded_in_history(web, make_ticket):
    ticket = make_ticket(status=Ticket.OPEN_STATUS)
    drag(web, ticket, Ticket.RESOLVED_STATUS)
    assert FollowUp.objects.filter(ticket=ticket, new_status=Ticket.RESOLVED_STATUS).exists()
