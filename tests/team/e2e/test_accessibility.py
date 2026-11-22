"""Accessibility checks with axe-core 4.10.2 (WCAG 2.0/2.1 A and AA rules).

AX-1  The screen chosen for the fix, the public ticket lookup form (/view/),
      has no critical or serious violations of its own. Before the fix its two
      inputs had no accessible name (axe rule `label`, critical) because the
      <label for="id_ticket"> elements pointed at inputs without that id.
AX-2  Survey of the six W1/W2 screens. Results are saved as evidence and the
      test fails only if a rule that was not in the baseline appears
      (regression guard), so known site-wide issues stay visible in the report.

Set A11Y_PHASE=before / after to label the evidence files.
"""

import json
import os
from pathlib import Path

import pytest

from .conftest import EVIDENCE, login

AXE = (Path(__file__).parent / "vendor" / "axe.min.js").read_text(encoding="utf-8")
PHASE = os.environ.get("A11Y_PHASE", "current")
TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]

# Rules axe reported on these screens at baseline (docs/team/ACCESSIBILITY.md).
# `list` comes from the shared navbar in base.html and is out of the fix scope.
BASELINE_RULES = {"color-contrast", "list", "label", "button-name", "link-name", "select-name"}


def axe(page):
    page.add_script_tag(content=AXE)
    return page.evaluate(
        "async (tags) => await axe.run(document, {runOnly: {type: 'tag', values: tags}})", TAGS
    )["violations"]


def save(name, violations):
    out = EVIDENCE.parent / "accessibility"
    out.mkdir(parents=True, exist_ok=True)
    summary = [
        {"rule": v["id"], "impact": v["impact"], "nodes": len(v["nodes"]),
         "targets": [n["target"] for n in v["nodes"]][:5], "help": v["help"]}
        for v in violations
    ]
    (out / f"axe_{name}_{PHASE}.json").write_text(json.dumps(summary, indent=2))
    return summary


def test_ax1_ticket_lookup_form_inputs_have_accessible_names(page):
    page.goto("/view/")
    found = save("view_lookup", axe(page))
    own = [v for v in found if v["impact"] in ("critical", "serious") and v["rule"] != "list"]
    assert own == [], own
    # the names a screen reader announces
    assert page.get_by_label("Ticket").count() == 1
    assert page.get_by_label("Your E-mail Address").count() == 1


SCREENS = [
    ("home", None, "/"),
    ("public_submit", None, "/tickets/submit/"),
    ("view_lookup", None, "/view/"),
    ("login", None, "/login/"),
    ("staff_submit", "alice", "/tickets/submit/"),
    ("staff_ticket", "alice", "/tickets/1/"),
]


@pytest.mark.parametrize("name, user, path", SCREENS, ids=[s[0] for s in SCREENS])
def test_ax2_survey_no_new_violation_types(page, name, user, path):
    if user:
        login(page, user)
    page.goto(path)
    found = save(f"survey_{name}", axe(page))
    new = {v["rule"] for v in found} - BASELINE_RULES
    assert not new, f"new accessibility rule violations on {name}: {sorted(new)}"
