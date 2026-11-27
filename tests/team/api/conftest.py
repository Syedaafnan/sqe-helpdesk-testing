"""Shared fixtures for API and integration tests.

Every test gets a fresh, rolled-back database from pytest-django, so no reset
is needed between tests. Test data comes from the generator output in
tests/team/datagen/generated/cases.json.
"""

import json
import os
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from helpdesk.models import FollowUp, Queue, Ticket, TicketDependency
from tests.team.seed import content as cafe

GENERATED = Path(__file__).resolve().parents[1] / "datagen" / "generated"
# TEAM_CASES=cases_v2.json runs the same tests on the regenerated (changed-spec) cases.
CASES_FILE = GENERATED / os.environ.get("TEAM_CASES", "cases.json")

OPEN, REOPENED, RESOLVED, CLOSED, DUPLICATE = 1, 2, 3, 4, 5
ALL_STATUSES = (OPEN, REOPENED, RESOLVED, CLOSED, DUPLICATE)
FLOW = Ticket.STATUS_CHOICES_FLOW


def load_cases(operation):
    data = json.loads(CASES_FILE.read_text())
    return [c for c in data["cases"] if c["operation"] == operation]


def start_state_for(target):
    """A starting status from which moving to ``target`` is allowed (BR-3).

    Prefers a real change of state; falls back to ``target`` itself (staying put)
    when no other status may reach it, e.g. Open.
    """
    for status in ALL_STATUSES:
        if status != target and target in FLOW.get(status, ()):
            return status
    return target


@pytest.fixture
def queue(db):
    return Queue.objects.create(
        title=cafe.MAIN_QUEUE, slug=cafe.MAIN_QUEUE_SLUG, allow_public_submission=True
    )


@pytest.fixture
def staff_user(db):
    return get_user_model().objects.create_user(
        username=cafe.W2_STAFF, email=f"{cafe.W2_STAFF}@{cafe.DOMAIN}", password="Pa33w0rd!", is_staff=True
    )


@pytest.fixture
def submitter_user(db):
    return get_user_model().objects.create_user(
        username=cafe.CUSTOMER[0], email=cafe.CUSTOMER_EMAIL, password="Pa33w0rd!"
    )


@pytest.fixture
def staff_client(staff_user):
    client = APIClient()
    client.force_authenticate(staff_user)
    return client


@pytest.fixture
def submitter_client(submitter_user):
    client = APIClient()
    client.force_authenticate(submitter_user)
    return client


@pytest.fixture
def anon_client():
    return APIClient()


@pytest.fixture
def make_ticket(queue):
    def _make(status=OPEN, email=cafe.CUSTOMER_EMAIL, title="Wi-Fi drops during a match", **kw):
        return Ticket.objects.create(
            queue=queue, title=title, status=status, submitter_email=email, **kw
        )

    return _make


@pytest.fixture
def add_open_dependency(make_ticket):
    def _add(ticket):
        blocker = make_ticket(status=OPEN, title="Blocking ticket")
        TicketDependency.objects.create(ticket=ticket, depends_on=blocker)
        return blocker

    return _add


def followup_count(ticket):
    return FollowUp.objects.filter(ticket=ticket).count()
