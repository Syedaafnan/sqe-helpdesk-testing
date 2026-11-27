"""BR-2 decision table through the submitter's HTTP endpoint (POST /view/).

    C1 no open dependencies | C2 status unchanged | C3 allowed by flow -> outcome
    R1   T                  |   -                 |   T                -> accept (302)
    R2   T                  |   -                 |   F                -> reject (403)
    R3   F                  |   T                 |   T                -> accept (302)
    R4   F                  |   F                 |   -                -> reject (403)

Each rule is tested, plus the extra combinations needed to show every
condition independently (C1=F with an allowed change, C2=T without deps).
The shared Ticket record is read back after every request.
"""

import pytest
from django.test import Client

from helpdesk.models import FollowUp
from tests.team.seed import content as cafe

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def post_as_submitter(ticket, new_status, email=None, key=None, comment="Update from submitter"):
    url = (
        f"/view/?ticket={ticket.queue.slug}-{ticket.id}"
        f"&email={email or ticket.submitter_email}&key={key or ticket.secret_key}"
    )
    return Client().post(url, {"new_status": new_status, "comment": comment})


DECISION_TABLE = [
    # id,                     start, new, open_dep, expected_http, final_status
    ("R1 deps=F allowed",      1,     3,   False,    302,           3),
    ("R1b deps=F same",        1,     1,   False,    302,           1),
    ("R2 deps=F disallowed",   4,     3,   False,    403,           4),
    ("R3 deps=T same",         1,     1,   True,     302,           1),
    ("R4 deps=T allowed",      1,     3,   True,     403,           1),
    ("R4b deps=T disallowed",  4,     3,   True,     403,           4),
]


@pytest.mark.parametrize(
    "start, new, open_dep, http, final",
    [d[1:] for d in DECISION_TABLE],
    ids=[d[0] for d in DECISION_TABLE],
)
def test_br2_decision_table(start, new, open_dep, http, final, make_ticket, add_open_dependency):
    ticket = make_ticket(status=start)
    if open_dep:
        add_open_dependency(ticket)
    before = FollowUp.objects.filter(ticket=ticket).count()

    response = post_as_submitter(ticket, new)

    assert response.status_code == http
    ticket.refresh_from_db()
    assert ticket.status == final
    after = FollowUp.objects.filter(ticket=ticket).count()
    assert after == (before + 1 if http == 302 else before)


@pytest.mark.parametrize("field", ["email", "key"])
def test_wrong_credentials_denied(field, make_ticket):
    """FR-09: a submitter can only update their own ticket."""
    ticket = make_ticket(status=1)
    kwargs = {"email": f"intruder@{cafe.DOMAIN}"} if field == "email" else {"key": "wrongkey"}

    response = post_as_submitter(ticket, 3, **kwargs)

    assert response.status_code == 403
    ticket.refresh_from_db()
    assert ticket.status == 1


def test_non_numeric_status_denied(make_ticket):
    ticket = make_ticket(status=1)
    assert post_as_submitter(ticket, "abc").status_code == 403
    ticket.refresh_from_db()
    assert ticket.status == 1
