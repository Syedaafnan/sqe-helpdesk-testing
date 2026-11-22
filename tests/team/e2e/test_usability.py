"""Usability task tests (docs/team/USABILITY.md).

UX-T1  Customer submits a ticket, makes a typing mistake in the e-mail
       address, is told what is wrong, corrects it and succeeds.
UX-T2  Customer submits a ticket using only the keyboard (no mouse).

Each test records task time and the number of user actions to
docs/team/evidence/usability/<task>.json for the usability report.
"""

import json
import re
import time

from playwright.sync_api import expect

from .conftest import CUSTOMER_EMAIL, EVIDENCE, field, unique


def record(task, **data):
    out = EVIDENCE.parent / "usability"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{task}.json").write_text(json.dumps(data, indent=2))


def test_uxt1_rejected_email_then_fixed(page):
    start, actions = time.monotonic(), 0
    title = unique("Projector no signal")
    page.goto("/tickets/submit/")
    page.select_option("#id_queue", label="IT Support"); actions += 1
    page.fill("#id_title", title); actions += 1
    page.fill("#id_body", "The projector in room 4 shows no signal."); actions += 1
    page.fill("#id_submitter_email", "sam.rivera@example"); actions += 1   # mistake: no TLD dot? accepted by HTML5
    page.fill("#id_submitter_email", "sam.rivera@"); actions += 1          # mistake the browser rejects
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
    title = unique("Keyboard only")
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

    page.keyboard.type("IT")          # type-ahead selects "IT Support"
    keys += 1
    assert page.eval_on_selector("#id_queue", "e => e.options[e.selectedIndex].text") == "IT Support"
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
