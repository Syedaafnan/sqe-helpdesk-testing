"""Controlled failure and recovery on the W2 write path (docs/team/PERFORMANCE.md).

Fault injected: the database rejects the follow-up INSERT once (as with a
locked SQLite file or a dropped connection) while a ticket is being resolved
through POST /api/followups/. Then the fault is removed and the request is
retried, as a client would.

Checks: the error is reported (not swallowed), the persisted state is
consistent, the retry succeeds without duplicates, and other tickets are
unaffected once the fault clears.
"""

from contextlib import contextmanager
from unittest import mock

import pytest
from django.db import OperationalError
from rest_framework.test import APIClient

from helpdesk.models import FollowUp, Ticket, TicketChange

pytestmark = [pytest.mark.recovery, pytest.mark.django_db]

RESOLVE = {"comment": "Fixed the cable", "new_status": Ticket.RESOLVED_STATUS}


@pytest.fixture
def client(staff_user):
    c = APIClient(raise_request_exception=False)  # see the 500 the user would get
    c.force_authenticate(staff_user)
    return c


@contextmanager
def followup_insert_fails_once():
    real_save = FollowUp.save
    state = {"failed": False}

    def flaky_save(self, *args, **kwargs):
        if self.pk is None and not state["failed"]:
            state["failed"] = True
            raise OperationalError("database is locked")
        return real_save(self, *args, **kwargs)

    with mock.patch.object(FollowUp, "save", flaky_save):
        yield state


def resolve(client, ticket):
    return client.post("/api/followups/", {"ticket": ticket.id, **RESOLVE}, format="json")


def test_rec01_failure_is_reported_and_no_followup_is_written(client, make_ticket):
    ticket = make_ticket(status=Ticket.OPEN_STATUS)
    before = FollowUp.objects.filter(ticket=ticket).count()
    with followup_insert_fails_once() as fault:
        r = resolve(client, ticket)
    assert fault["failed"]
    assert r.status_code == 500
    assert FollowUp.objects.filter(ticket=ticket).count() == before


@pytest.mark.xfail(strict=True, reason="DEF-13: status is saved before the follow-up, outside a transaction")
def test_rec02_failed_update_leaves_ticket_status_unchanged(client, make_ticket):
    ticket = make_ticket(status=Ticket.OPEN_STATUS)
    with followup_insert_fails_once():
        resolve(client, ticket)
    ticket.refresh_from_db()
    assert ticket.status == Ticket.OPEN_STATUS  # actual: RESOLVED with no follow-up


@pytest.mark.xfail(strict=True, reason="DEF-13: the retry finds the status already changed and records no status change")
def test_rec03_retry_after_recovery_records_exactly_one_status_change(client, make_ticket):
    ticket = make_ticket(status=Ticket.OPEN_STATUS)
    with followup_insert_fails_once():
        resolve(client, ticket)
    retry = resolve(client, ticket)  # fault removed
    assert retry.status_code == 201
    ticket.refresh_from_db()
    assert ticket.status == Ticket.RESOLVED_STATUS
    assert FollowUp.objects.filter(ticket=ticket, new_status=Ticket.RESOLVED_STATUS).count() == 1
    assert TicketChange.objects.filter(followup__ticket=ticket, field="Status").count() == 1


def test_rec04_retry_succeeds_and_creates_no_duplicate(client, make_ticket):
    ticket = make_ticket(status=Ticket.OPEN_STATUS)
    with followup_insert_fails_once():
        resolve(client, ticket)
    retry = resolve(client, ticket)
    assert retry.status_code == 201
    ticket.refresh_from_db()
    assert ticket.status == Ticket.RESOLVED_STATUS
    assert FollowUp.objects.filter(ticket=ticket, comment=RESOLVE["comment"]).count() == 1


def test_rec05_other_tickets_work_normally_after_the_fault(client, make_ticket):
    first, second = make_ticket(status=Ticket.OPEN_STATUS), make_ticket(status=Ticket.OPEN_STATUS)
    with followup_insert_fails_once():
        resolve(client, first)
    r = resolve(client, second)
    assert r.status_code == 201
    second.refresh_from_db()
    assert second.status == Ticket.RESOLVED_STATUS
    assert FollowUp.objects.filter(ticket=second, new_status=Ticket.RESOLVED_STATUS).count() == 1
