# Usability and Accessibility

Tests: [`tests/team/e2e/test_usability.py`](../../tests/team/e2e/test_usability.py),
[`test_accessibility.py`](../../tests/team/e2e/test_accessibility.py).
Tools: Playwright 1.55 (Chromium), axe-core 4.10.2 (vendored, WCAG 2.0/2.1
A + AA rules), Lighthouse 12.2.1 (Chrome, headless).
Evidence: `evidence/usability/`, `evidence/accessibility/`, `evidence/e2e/`.

## 1. Usability task tests

Both tasks are on W1 (the customer's first contact) and record task time and
user actions.

| Task | Scenario | Success criterion | Measured | Result |
|---|---|---|---|---|
| **UX-T1** rejected value, then fix | Customer fills the public form, types `sam.rivera@` as e-mail, submits, reads the message, corrects the address, submits again. | Rejection keeps all other input; the message names the problem; focus moves to the bad field; second submit succeeds. | 8 actions, 1 error before success, 1.7 s automated. Message: *"Please enter a part following '@'. 'sam.rivera@' is incomplete."* Focus on `id_submitter_email`. Other fields kept. | **Pass** |
| **UX-T2** keyboard only | Customer completes the public form with Tab, typing and Enter only. | Every field and the submit button reachable by Tab in a logical order; visible focus indicator; ticket created. | 19 key presses, 5 Tabs from page top to the first field (skipping navbar links), focus outline present, queue chosen by type-ahead, submitted with Enter. | **Pass** |

Observations from writing and running the tasks (not failures of these tests):

| ID | Observation | Severity | Suggestion |
|---|---|---|---|
| UX-1 | E-mail format is checked only by the browser. `sam.rivera@example` (no dot in the domain) is accepted. | Low | Server-side check of the domain part. |
| UX-2 | `/view/` search by ticket id and e-mail does not open the ticket (the key from the e-mail is required), and the page shows no message. | Medium | Say "Use the link in your confirmation e-mail" when the key is missing. |
| UX-3 | The staff Respond form hides priority, owner and due date behind *Update ticket details*. Changing priority needs the extra click. | Low | Keep, but show the current values next to the button. |

## 2. Accessibility: chosen screen and fix

**Screen:** the public ticket lookup form `/view/`. It's on the customer's
path in W1/W2 (UC-1 A2, UC-4 E1), and axe found a critical violation there.

| | Before | After |
|---|---|---|
| axe `label` (critical) | **2 nodes**: the *Ticket* and *Your E-mail Address* inputs have no accessible name | 0 |
| axe `list` (serious) | **1 node**: navbar `<ul>` contains a `<div>` | 0 |
| Lighthouse accessibility | **91** (failing audits: `label`, `list`) | **100** |
| Lighthouse best practices | 96 | 96 |
| Screen-reader name of the inputs | none | "Ticket", "Your E-mail Address" (AX-1 `get_by_label`) |

**Cause.** The template already had `<label for="id_ticket">` and
`<label for="id_email">`, but the inputs had no `id`, so the labels pointed at
nothing. In the shared navbar the username was wrapped in a `<div>` directly
inside the `<ul>`.

**Fix (DEF-15)**, 4 changed lines:

```diff
- <input class="form-control" type="text" name="ticket" />
+ <input class="form-control" type="text" name="ticket" id="id_ticket" required />
- <input class="form-control" type="email" name="email" />
+ <input class="form-control" type="email" name="email" id="id_email" autocomplete="email" required />
  (navigation-header.html)
- <div class="nav-item"> ... </div>
+ <li class="nav-item"> ... </li>
```

Reports: `lighthouse_view_before.report.html`, `lighthouse_view_after.report.html`,
`axe_view_lookup_before.json`, `axe_view_lookup_after.json`.

## 3. Survey of the W1/W2 screens (axe, before and after)

| Screen | Before | After | Note |
|---|---|---|---|
| Home `/` | color-contrast (1), list (1) | color-contrast (1) | navbar fix removed `list` |
| Public submit `/tickets/submit/` | list (1) | **none** | navbar fix |
| Ticket lookup `/view/` | label (2, critical), list (1) | **none** | fixed screen |
| Login `/login/` | none | none | |
| Staff submit | button-name (1, critical) | button-name (1) | sidebar toggle has no text: out of fix scope |
| Staff ticket page | button-name, label, select-name (critical); color-contrast, link-name, list (3) | unchanged | out of fix scope; recorded for the backlog |

AX-2 fails if a **new** rule type appears on any of these screens (regression
guard). The remaining staff-screen issues are listed as follow-up work in the
test completion report.
