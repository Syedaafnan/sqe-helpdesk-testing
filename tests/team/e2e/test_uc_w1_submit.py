"""W1 Submit Ticket use cases (docs/team/USE_CASES.md).

UC-1  Customer submits a ticket through the public form   (Member 1)
UC-2  Staff member logs a ticket for a customer           (Member 1)

Each use case: main flow, alternative flows A1 and A2, exception flows E1 and E2.
"""

import re

from playwright.sync_api import expect

from .conftest import CUSTOMER_EMAIL, field, login, submit_public, submit_staff, unique


# ------------------------------------------------------------------- UC-1
def test_uc1_main_customer_submits_ticket(page):
    title = unique("Printer jammed")
    view_url, _ = submit_public(page, title)
    expect(page.locator("h2")).to_have_text(title)
    assert field(page, "STATUS") == "Open"                  # shared record created as Open
    assert field(page, "SUBMITTED BY") == CUSTOMER_EMAIL
    assert field(page, "QUEUE") == "IT Support"


def test_uc1_a1_customer_chooses_priority(page):
    submit_public(page, unique("VPN drops"), priority=2)
    assert field(page, "PRIORITY") == "2. High"


def test_uc1_a2_customer_returns_later_with_emailed_link(page, new_page):
    """The confirmation link (ticket, e-mail, secret key) opens the ticket in
    a fresh browser session. Searching /view/ by ticket id and e-mail alone
    does not open it (key required) - recorded as usability observation UX-2."""
    title = unique("Mailbox full")
    view_url, _ = submit_public(page, title)
    later = new_page()
    later.goto(view_url)
    expect(later.locator("h2")).to_have_text(title)
    assert field(later, "STATUS") == "Open"


def test_uc1_e1_required_fields_missing_is_blocked(page):
    page.goto("/tickets/submit/")
    page.click("button:has-text('Create Ticket')")
    assert page.url.endswith("/tickets/submit/")            # no navigation, no ticket
    message = page.eval_on_selector("#id_queue", "e => e.validationMessage")
    assert message                                         # browser explains what is missing


def test_uc1_e2_invalid_email_is_rejected(page):
    page.goto("/tickets/submit/")
    page.select_option("#id_queue", label="IT Support")
    page.fill("#id_title", unique("Bad email"))
    page.fill("#id_body", "x")
    page.fill("#id_submitter_email", "sam.rivera@")
    page.click("button:has-text('Create Ticket')")
    assert page.url.endswith("/tickets/submit/")
    assert page.eval_on_selector("#id_submitter_email", "e => e.validity.valid") is False


# ------------------------------------------------------------------- UC-2
def test_uc2_main_staff_logs_ticket_for_customer(page):
    login(page, "alice")
    title = unique("Laptop will not boot")
    submit_staff(page, title)
    expect(page.get_by_text(title).first).to_be_visible()
    assert field(page, "STATUS") == "Open"
    assert field(page, "QUEUE") == "IT Support"


def test_uc2_a1_staff_assigns_case_owner_on_creation(page):
    login(page, "alice")
    submit_staff(page, unique("Monitor flicker"), owner="bruno")
    assert page.eval_on_selector("#id_owner", "e => e.options[e.selectedIndex].text").strip() == "bruno"


def test_uc2_a2_staff_logs_ticket_without_customer_email(page):
    login(page, "alice")
    ticket_id = submit_staff(page, unique("Walk-in request"), email=None, priority=1)
    assert page.url.endswith(f"/tickets/{ticket_id}/")
    assert field(page, "PRIORITY") == "1. Critical"


def test_uc2_e1_queue_not_selected_is_blocked(page):
    login(page, "alice")
    page.goto("/tickets/submit/")
    page.fill("#id_title", unique("No queue"))
    page.fill("#id_body", "x")
    page.click("button:has-text('Submit Ticket')")
    assert page.url.endswith("/tickets/submit/")
    assert page.eval_on_selector("#id_queue", "e => e.validity.valueMissing") is True


def test_uc2_e2_title_longer_than_200_is_cut_to_the_limit(page):
    """BR-1 at the UI: the summary field stops at 200 characters (BVA 201)."""
    login(page, "alice")
    page.goto("/tickets/submit/")
    page.select_option("#id_queue", label="IT Support")
    page.fill("#id_title", "T" * 201)
    assert len(page.input_value("#id_title")) == 200
    page.fill("#id_body", "x")
    page.click("button:has-text('Submit Ticket')")
    page.wait_for_url(re.compile(r"/tickets/\d+/$"))
    expect(page.get_by_text("T" * 200).first).to_be_visible()
