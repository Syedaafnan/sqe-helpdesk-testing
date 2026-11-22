"""W2 Update / Resolve Ticket use cases (docs/team/USE_CASES.md).

UC-3  Staff member resolves a ticket                      (Member 2)
UC-4  Customer follows up through the ticket link         (Member 2)

Each use case: main flow, alternative flows A1 and A2, exception flows E1 and E2.
"""

import pytest
from playwright.sync_api import expect

from .conftest import (
    add_dependency,
    field,
    login,
    respond,
    status_radios,
    submit_public,
    submit_staff,
    unique,
)


@pytest.fixture
def staff(page):
    login(page, "alice")
    return page


def resolved_ticket(staff_page, customer_page):
    """A customer ticket that staff has resolved. Returns (view_url, id)."""
    view_url, ticket_id = submit_public(customer_page, unique("Needs a fix"))
    respond(staff_page, ticket_id, "Replaced the cable.", status="resolved")
    return view_url, ticket_id


# ------------------------------------------------------------------- UC-3
def test_uc3_main_staff_resolves_ticket(staff):
    ticket_id = submit_staff(staff, unique("Disk full"))
    respond(staff, ticket_id, "Cleared old logs.", status="resolved")
    assert field(staff, "STATUS") == "Resolved"
    expect(staff.get_by_text("Changed Status from Open to Resolved.")).to_be_visible()
    expect(staff.locator(".alert-success")).to_contain_text("Cleared old logs.")


def test_uc3_a1_comment_only_keeps_status(staff):
    ticket_id = submit_staff(staff, unique("Slow Wi-Fi"))
    respond(staff, ticket_id, "Looking into it.")
    assert field(staff, "STATUS") == "Open"
    expect(staff.get_by_text("Looking into it.").first).to_be_visible()


def test_uc3_a2_staff_closes_directly_from_open(staff):
    ticket_id = submit_staff(staff, unique("Already fixed"))
    respond(staff, ticket_id, "User fixed it themselves.", status="closed")
    assert field(staff, "STATUS") == "Closed"
    assert status_radios(staff) == ["st_reopened", "st_closed"]  # BR-3 flow from Closed


def test_uc3_e1_open_dependency_blocks_resolution(staff):
    blocker = submit_staff(staff, unique("Blocker"))
    ticket_id = submit_staff(staff, unique("Depends on blocker"))
    add_dependency(staff, ticket_id, blocker)
    staff.goto(f"/tickets/{ticket_id}/")
    staff.click("button:has-text('Respond')")
    assert staff.is_disabled("#st_resolved") and staff.is_disabled("#st_closed")
    expect(staff.get_by_text("cannot be resolved or closed until the tickets it depends on are resolved")).to_be_visible()


def test_uc3_e2_closed_ticket_cannot_be_resolved(staff):
    ticket_id = submit_staff(staff, unique("Closed one"))
    respond(staff, ticket_id, "Closing.", status="closed")
    staff.click("button:has-text('Respond')")
    assert "st_resolved" not in status_radios(staff)          # BR-3: Closed -> Resolved not offered


# ------------------------------------------------------------------- UC-4
def test_uc4_main_customer_adds_comment(page):
    view_url, _ = submit_public(page, unique("Keyboard missing keys"))
    page.fill("#commentBox", "It is the F5 key.")
    page.click("button:has-text('Update This Ticket')")
    page.wait_for_load_state()
    expect(page.get_by_text("It is the F5 key.").first).to_be_visible()
    assert field(page, "STATUS") == "Open"


def test_uc4_a1_customer_accepts_resolution_and_closes(page, new_page):
    login(page, "alice")
    customer = new_page()
    view_url, _ = resolved_ticket(page, customer)
    customer.goto(view_url)
    customer.click("a:has-text('Accept and Close')")
    customer.wait_for_load_state()
    assert field(customer, "STATUS") == "Closed"


def test_uc4_a2_customer_reopens_resolved_ticket(page, new_page):
    login(page, "alice")
    customer = new_page()
    view_url, _ = resolved_ticket(page, customer)
    customer.goto(view_url)
    customer.fill("#commentBox", "Still broken after the fix.")
    customer.check("#st_reopened")
    customer.click("button:has-text('Update This Ticket')")
    customer.wait_for_load_state()
    assert field(customer, "STATUS") == "Reopened"


def test_uc4_e1_wrong_secret_key_shows_no_ticket(page):
    title = unique("Private problem")
    view_url, _ = submit_public(page, title)
    page.goto(view_url.replace("key=", "key=0"))
    expect(page.get_by_text(title)).to_have_count(0)
    expect(page.locator("input[name=ticket]")).to_be_visible()   # back to the search form


def test_uc4_e2_open_dependency_disables_customer_status_change(page, new_page):
    login(page, "alice")
    customer = new_page()
    view_url, ticket_id = resolved_ticket(page, customer)
    blocker = submit_staff(page, unique("Blocker for customer"))
    add_dependency(page, ticket_id, blocker)
    customer.goto(view_url)
    assert customer.is_disabled("#st_reopened") and customer.is_disabled("#st_closed")
    expect(customer.get_by_text("cannot be resolved or closed until the tickets it depends on are resolved")).to_be_visible()
