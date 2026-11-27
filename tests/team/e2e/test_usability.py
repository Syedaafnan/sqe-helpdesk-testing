"""Usability task tests (final report, Usability and Accessibility).

UX-T1  Customer submits a ticket, makes a typing mistake in the e-mail
       address, is told what is wrong, corrects it and succeeds.
UX-T2  Customer submits a ticket using only the keyboard (no mouse).
UX-T3  Staff resolves a customer's ticket from the ticket page (W2) and sees
       the confirmation: new status, status-change note and the comment.

Each test records task time and the number of user actions to
docs/team/evidence/usability/<task>.json for the usability report.
"""

import json
import re
import time

from playwright.sync_api import expect

from tests.team.seed import content as cafe

from .conftest import CUSTOMER_EMAIL, EVIDENCE, field, login, submit_staff, unique


def record(task, **data):
    out = EVIDENCE.parent / "usability"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{task}.json").write_text(json.dumps(data, indent=2))


def test_uxt1_rejected_email_then_fixed(page):
    start, actions = time.monotonic(), 0
    title = unique("Ordering app takes forever")
    page.goto("/tickets/submit/")
    page.select_option("#id_queue", label=cafe.MAIN_QUEUE); actions += 1
    page.fill("#id_title", title); actions += 1
    page.fill("#id_body", "The app spins forever when I try to order a latte."); actions += 1
    page.fill("#id_submitter_email", cafe.CUSTOMER_EMAIL.rsplit(".", 1)[0]); actions += 1   # mistake: no TLD dot? accepted by HTML5
    page.fill("#id_submitter_email", cafe.CUSTOMER_EMAIL.split("@")[0] + "@"); actions += 1          # mistake the browser rejects
    page.click("button:has-text('Create Ticket')"); actions += 1

    # rejected: still on the form, the field says why and has focus
    assert page.url.endswith("/tickets/submit/")
    message = page.eval_on_selector("#id_submitter_email", "e => e.validationMessage")
    assert message
    assert page.evaluate("document.activeElement.id") == "id_submitter_email"

    # fix and resubmit
    page.fill("#id_submitter_email", CUSTOMER_EMAIL); actions += 1
    page.click("button:has-text('Create Ticket')"); actions += 1
    page.wait_for_url(re.compile(r"/view/\?ticket="))
    expect(page.locator("h2")).to_have_text(title)
    assert field(page, "STATUS") == "Open"
    record("uxt1_rejected_then_fixed", seconds=round(time.monotonic() - start, 2),
           actions=actions, error_message=message, errors_before_success=1, success=True)


def test_uxt2_keyboard_only_submission(page):
    start, keys = time.monotonic(), 0
    title = unique("Keyboard only: slow Wi-Fi")
    page.goto("/tickets/submit/")

    def press(key):
        nonlocal keys
        page.keyboard.press(key)
        keys += 1

    # Tab from the top of the page to the first form field
    tabs_to_form = 0
    while page.evaluate("document.activeElement.id") != "id_queue":
        press("Tab")
        tabs_to_form += 1
        assert tabs_to_form < 40, "queue field is not reachable with Tab"

    # visible focus indicator on the focused control (WCAG 2.4.7)
    outline = page.evaluate(
        "(() => { const s = getComputedStyle(document.activeElement);"
        " return s.outlineStyle !== 'none' || s.boxShadow !== 'none'; })()"
    )
    assert outline, "focused field has no visible focus indicator"

    page.keyboard.type("Cafe")        # type-ahead selects "Cafe Wi-Fi"
    keys += 1
    assert page.eval_on_selector("#id_queue", "e => e.options[e.selectedIndex].text") == cafe.MAIN_QUEUE
    press("Tab"); page.keyboard.type(title); keys += 1
    press("Tab"); page.keyboard.type("Submitted without a mouse."); keys += 1
    press("Tab")                      # priority: keep the default 3. Normal
    assert page.evaluate("document.activeElement.id") == "id_priority"

    # continue tabbing to the e-mail field, then to the submit button
    while page.evaluate("document.activeElement.id") != "id_submitter_email":
        press("Tab")
        assert keys < 80
    page.keyboard.type(CUSTOMER_EMAIL); keys += 1
    while page.evaluate("document.activeElement.textContent.trim()") != "Create Ticket":
        press("Tab")
        assert keys < 120, "submit button is not reachable with Tab"
    press("Enter")

    page.wait_for_url(re.compile(r"/view/\?ticket="))
    expect(page.locator("h2")).to_have_text(title)
    record("uxt2_keyboard_only", seconds=round(time.monotonic() - start, 2),
           key_presses=keys, tabs_to_first_field=tabs_to_form, mouse_used=False, success=True)


def test_uxt3_staff_resolves_ticket(page):
    # setup (not part of the task): a customer's open ticket in the cafe desk
    login(page, cafe.W2_STAFF)
    ticket_id = submit_staff(page, unique("Wi-Fi drops in the gaming lounge"))

    # task: open the ticket screen, record the fix and resolve it
    start, actions = time.monotonic(), 0
    page.goto(f"/tickets/{ticket_id}/")
    assert field(page, "STATUS") == "Open"
    page.click("button:has-text('Respond')"); actions += 1
    page.fill("#commentBox", "Restarted the lounge router and moved PCs to the 5 GHz band."); actions += 1
    page.check("#st_resolved"); actions += 1
    page.click("#ticket-respond-form button:has-text('Save')"); actions += 1
    page.wait_for_load_state()

    # confirmation shown to the user, and the shared record changed
    assert field(page, "STATUS") == "Resolved"
    expect(page.get_by_text("Changed Status from Open to Resolved.")).to_be_visible()
    expect(page.locator(".alert-success")).to_contain_text("Restarted the lounge router")
    record("uxt3_staff_resolves_ticket", seconds=round(time.monotonic() - start, 2),
           actions=actions, confirmation="Changed Status from Open to Resolved.", success=True)
