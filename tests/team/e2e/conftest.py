"""Shared Playwright fixtures and page helpers for the end-to-end tests.

The tests drive the running demo site (see final report, Appendix A):

    python manage.py demo_data --reset
    python tests/team/seed/seed_butter_bean.py
    python manage.py runserver 0.0.0.0:8080

The tests use the team scenario from tests/team/seed/content.py: the support
desk of Butter & Bean, a gaming cafe in Islamabad (synthetic people and data).
    pytest tests/team/e2e -m e2e

E2E_BASE_URL overrides the address. If the site is not reachable the tests are
skipped, unless E2E_REQUIRED=1 (set in CI) which turns that into a failure.
Every test creates its own tickets with a unique title, so tests do not depend
on each other or on the order they run in.

A screenshot of the final page of every test is written to
docs/team/evidence/e2e/<test name>.png.
"""

import contextlib
import os
import re
import urllib.request
import uuid
from pathlib import Path

import pytest

from tests.team.seed import content as cafe

os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8080").rstrip("/")
PASSWORD = cafe.PASSWORD
CUSTOMER_EMAIL = cafe.CUSTOMER_EMAIL
EVIDENCE = Path(__file__).resolve().parents[3] / "docs" / "team" / "evidence" / "e2e"


def _site_up():
    try:
        with urllib.request.urlopen(BASE_URL + "/", timeout=5) as r:
            return r.status == 200
    except OSError:
        return False


def pytest_collection_modifyitems(items):
    e2e = [i for i in items if "tests/team/e2e/" in str(i.fspath).replace("\\", "/")]
    for item in e2e:
        item.add_marker(pytest.mark.e2e)
    if e2e and not _site_up():
        if os.environ.get("E2E_REQUIRED") == "1":
            raise pytest.UsageError(f"E2E_REQUIRED=1 but {BASE_URL} is not reachable")
        skip = pytest.mark.skip(reason=f"demo site {BASE_URL} not reachable")
        for item in e2e:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture
def page(browser, request):
    context = browser.new_context(base_url=BASE_URL, viewport={"width": 1280, "height": 900})
    context.set_default_timeout(15000)
    pg = context.new_page()
    yield pg
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"[^\w.-]+", "_", request.node.name)[:120]
    with contextlib.suppress(Exception):  # evidence only, never fail a test on it
        pg.screenshot(path=str(EVIDENCE / f"{name}.png"), full_page=True)
    context.close()


@pytest.fixture
def new_page(browser):
    """A second, independent browser session (e.g. customer next to staff)."""
    contexts = []

    def make():
        ctx = browser.new_context(base_url=BASE_URL, viewport={"width": 1280, "height": 900})
        ctx.set_default_timeout(15000)
        contexts.append(ctx)
        return ctx.new_page()

    yield make
    for ctx in contexts:
        ctx.close()


def unique(prefix):
    return f"{prefix} {uuid.uuid4().hex[:8]}"


# ------------------------------------------------------------------ helpers
def login(page, username):
    page.goto("/login/")
    page.fill("input[name=username]", username)
    page.fill("input[name=password]", PASSWORD)
    page.click("button:has-text('Log in')")
    page.wait_for_load_state()


def submit_public(page, title, email=CUSTOMER_EMAIL, queue=cafe.MAIN_QUEUE, priority=None, body="Created by E2E"):
    """W1 through the public form. Returns (view_url, ticket_id)."""
    page.goto("/tickets/submit/")
    page.select_option("#id_queue", label=queue)
    page.fill("#id_title", title)
    page.fill("#id_body", body)
    if priority:
        page.select_option("#id_priority", value=str(priority))
    page.fill("#id_submitter_email", email)
    page.click("button:has-text('Create Ticket')")
    page.wait_for_url(re.compile(r"/view/\?ticket="))
    label = re.search(r"ticket=([A-Za-z0-9]+-(\d+))", page.url)
    return page.url, int(label.group(2))


def submit_staff(page, title, email=CUSTOMER_EMAIL, queue=cafe.MAIN_QUEUE, owner=None, priority=None):
    """W1 through the staff form (already logged in). Returns ticket id."""
    page.goto("/tickets/submit/")
    page.select_option("#id_queue", label=queue)
    page.fill("#id_title", title)
    page.fill("#id_body", "Logged by staff during E2E")
    if email:
        page.fill("#id_submitter_email", email)
    if owner:
        page.select_option("#id_assigned_to", label=owner)
    if priority:
        page.select_option("#id_priority", value=str(priority))
    page.click("button:has-text('Submit Ticket')")
    page.wait_for_url(re.compile(r"/tickets/\d+/$"))
    return int(re.search(r"/tickets/(\d+)/$", page.url).group(1))


def respond(page, ticket_id, comment="", status=None, **fields):
    """W2 through the staff Respond tab (already logged in)."""
    page.goto(f"/tickets/{ticket_id}/")
    page.click("button:has-text('Respond')")
    if comment:
        page.fill("#commentBox", comment)
    if status:
        page.check(f"#st_{status}")
    if fields:
        page.click("a:has-text('Update ticket details')")
        page.wait_for_selector("#collapseDetails.show")
    if "priority" in fields:
        page.select_option("#id_priority", value=str(fields["priority"]))
    if "owner" in fields:
        page.select_option("#id_owner", label=fields["owner"])
    if "due_date" in fields:
        page.fill("#id_due_date", fields["due_date"])
    page.click("#ticket-respond-form button:has-text('Save')")
    page.wait_for_load_state()


def field(page, label):
    """Value shown under an upper-case heading (STATUS, PRIORITY, QUEUE...)
    on the staff or public ticket page; the shared record as the user sees it."""
    return page.evaluate(
        """(label) => {
            const head = [...document.querySelectorAll('.text-uppercase, th, small')]
                .find(e => e.innerText.trim().toUpperCase() === label);
            if (!head) return null;
            return head.parentElement.innerText.replace(head.innerText, '').trim().split('\\n')[0].trim();
        }""",
        label.upper(),
    )


def add_dependency(page, ticket_id, depends_on_id):
    page.goto(f"/tickets/{ticket_id}/dependency/add/")
    page.select_option("#id_depends_on", value=str(depends_on_id))
    page.click("form:has(#id_depends_on) input[type=submit]")
    page.wait_for_load_state()


def status_radios(page):
    return [r.get_attribute("id") for r in page.query_selector_all("input[name=new_status]")]
