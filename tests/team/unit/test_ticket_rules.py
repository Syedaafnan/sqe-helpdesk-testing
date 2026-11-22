"""White-box unit tests for src/helpdesk/ticket_rules.py (BR-1..BR-4).

Target: 100% statement and branch coverage, plus MCC and MC/DC for BR-2.
Test IDs (UT-xx) are referenced from docs/team/TRACEABILITY.md.
"""

import pytest

from helpdesk import ticket_rules as r
from helpdesk.ticket_rules import RuleViolation

pytestmark = pytest.mark.unit

OPEN, REOPENED, RESOLVED, CLOSED, DUPLICATE = 1, 2, 3, 4, 5
ALL = (OPEN, REOPENED, RESOLVED, CLOSED, DUPLICATE)
FLOW = {  # copy of DEFAULT_TICKET_STATUS_CHOICES_FLOW
    OPEN: (OPEN, RESOLVED, CLOSED, DUPLICATE),
    REOPENED: (REOPENED, RESOLVED, CLOSED, DUPLICATE),
    RESOLVED: (REOPENED, RESOLVED, CLOSED),
    CLOSED: (REOPENED, CLOSED),
    DUPLICATE: (REOPENED, DUPLICATE),
}


def test_flow_copy_matches_application_default():
    """UT-00 guard: the table used here is the one the application ships."""
    from helpdesk.settings import DEFAULT_TICKET_STATUS_CHOICES_FLOW

    assert FLOW == DEFAULT_TICKET_STATUS_CHOICES_FLOW


# ----------------------------------------------------------------- BR-1 priority
@pytest.mark.parametrize(
    "value, expected",
    [(1, 1), (2, 2), (3, 3), (4, 4), (5, 5), ("1", 1), ("5", 5), (" 3 ", 3)],
)
def test_ut01_priority_valid_partition_and_boundaries(value, expected):
    assert r.validate_priority(value) == expected


@pytest.mark.parametrize("value", [0, 6, -1, 100, "0", "6"])
def test_ut02_priority_out_of_range_rejected(value):
    with pytest.raises(RuleViolation) as exc:
        r.validate_priority(value)
    assert exc.value.code == "priority_range"
    assert "from 1 (Critical) to 5 (Very Low)" in exc.value.message
    assert str(int(value)) in exc.value.message


@pytest.mark.parametrize("value", [True, False, 2.5, 3.0, "abc", "", None, [3]])
def test_ut03_priority_wrong_type_rejected(value):
    with pytest.raises(RuleViolation) as exc:
        r.validate_priority(value)
    assert exc.value.code == "priority_type"
    assert exc.value.message == "Priority must be a whole number from 1 to 5."


def test_ut04_priority_limits_are_1_and_5():
    assert (r.PRIORITY_MIN, r.PRIORITY_MAX) == (1, 5)


# ------------------------------------------------------------------- BR-1 title
@pytest.mark.parametrize("length", [1, 199, 200])
def test_ut05_title_length_valid_boundaries(length):
    assert r.validate_title("x" * length) == "x" * length


def test_ut06_title_201_rejected_with_count():
    with pytest.raises(RuleViolation) as exc:
        r.validate_title("x" * 201)
    assert exc.value.code == "title_too_long"
    assert "201 characters" in exc.value.message
    assert "200 characters or fewer" in exc.value.message


@pytest.mark.parametrize("title", ["", "   ", None, 42])
def test_ut07_title_missing_rejected(title):
    with pytest.raises(RuleViolation) as exc:
        r.validate_title(title)
    assert exc.value.code == "title_required"


def test_ut08_title_is_stripped():
    assert r.validate_title("  Printer jam  ") == "Printer jam"


# ------------------------------------------------------------ BR-3 state machine
ALLOWED = [(s, t) for s in ALL for t in FLOW[s] if s != t]
DISALLOWED = [(s, t) for s in ALL for t in ALL if t not in FLOW[s] and s != t]


@pytest.mark.parametrize("current, new", ALLOWED)
def test_ut09_every_allowed_transition(current, new):
    assert r.is_transition_allowed(current, new, FLOW, ALL) is True


@pytest.mark.parametrize("current, new", DISALLOWED)
def test_ut10_every_disallowed_transition(current, new):
    assert r.is_transition_allowed(current, new, FLOW, ALL) is False


@pytest.mark.parametrize("status", ALL)
def test_ut11_staying_in_same_status_is_allowed(status):
    assert r.is_transition_allowed(status, status, FLOW, ALL) is True


@pytest.mark.parametrize("bad", [0, 6, 99])
def test_ut12_unknown_target_status_rejected(bad):
    assert r.is_transition_allowed(OPEN, bad, FLOW, ALL) is False


def test_ut13_allowed_next_statuses_from_flow():
    assert r.allowed_next_statuses(CLOSED, FLOW, ALL) == (REOPENED, CLOSED)


def test_ut14_unmapped_status_may_move_anywhere():
    partial = {OPEN: (OPEN, RESOLVED)}
    assert r.allowed_next_statuses(CLOSED, partial, ALL) == ALL
    assert r.is_transition_allowed(CLOSED, OPEN, partial, ALL) is True


def test_ut15_empty_mapping_means_all_statuses():
    assert r.allowed_next_statuses(OPEN, {OPEN: ()}, ALL) == ALL


def test_ut16_counts_of_transitions():
    # 20 possible changes of state: 10 allowed and 10 disallowed in the default flow
    assert len(ALLOWED) == 10
    assert len(DISALLOWED) == 10


# ---------------------------------------- BR-2 decision: MCC (all 8 combinations)
# A = has_open_dependencies is False, B = new == current, C = transition allowed
# decision = (A or B) and C
# B=True forces C=True (staying put is always allowed), so B=T,C=F is infeasible.
MCC = [
    # id,   deps,  current, new,       A,     B,     C,     expected
    ("M1", False, OPEN, RESOLVED, True, False, True, True),
    ("M2", False, CLOSED, RESOLVED, True, False, False, False),
    ("M3", False, OPEN, OPEN, True, True, True, True),
    # M4 A=T,B=T,C=F infeasible
    ("M5", True, OPEN, RESOLVED, False, False, True, False),
    ("M6", True, CLOSED, RESOLVED, False, False, False, False),
    ("M7", True, OPEN, OPEN, False, True, True, True),
    # M8 A=F,B=T,C=F infeasible
]


@pytest.mark.parametrize(
    "case_id, deps, current, new, a, b, c, expected", MCC, ids=[m[0] for m in MCC]
)
def test_ut17_br2_mcc(case_id, deps, current, new, a, b, c, expected):
    # the inputs really produce the intended condition values
    assert (not deps) is a
    assert (new == current) is b
    assert r.is_transition_allowed(current, new, FLOW, ALL) is c
    assert r.submitter_may_change_status(current, new, deps, FLOW, ALL) is expected


# MC/DC pairs taken from the MCC table. Each pair differs in exactly one
# condition and the outcome flips, which shows that condition alone decides it:
#   A: M1 vs M5   (B=F, C=T held fixed)
#   B: M5 vs M7   (A=F, C=T held fixed)
#   C: M1 vs M2   (A=T, B=F held fixed)
# Minimum MC/DC test set: {M1, M2, M5, M7} = n + 1 = 4 tests.
MCDC_PAIRS = [("A", "M1", "M5"), ("B", "M5", "M7"), ("C", "M1", "M2")]


@pytest.mark.parametrize("cond, first, second", MCDC_PAIRS)
def test_ut18_br2_mcdc_pairs(cond, first, second):
    rows = {m[0]: m for m in MCC}
    r1, r2 = rows[first], rows[second]
    index = {"A": 4, "B": 5, "C": 6}[cond]
    others = [i for i in (4, 5, 6) if i != index]
    assert r1[index] != r2[index]
    assert all(r1[i] == r2[i] for i in others)
    out1 = r.submitter_may_change_status(r1[2], r1[3], r1[1], FLOW, ALL)
    out2 = r.submitter_may_change_status(r2[2], r2[3], r2[1], FLOW, ALL)
    assert out1 != out2


# ------------------------------------------- check_status_change (all write paths)
def test_ut19_check_status_change_returns_new_status():
    assert r.check_status_change(OPEN, RESOLVED, False, FLOW, ALL) == RESOLVED


def test_ut20_check_status_change_unchanged_with_open_dependencies():
    assert r.check_status_change(OPEN, OPEN, True, FLOW, ALL) == OPEN


def test_ut21_check_status_change_invalid_status():
    with pytest.raises(RuleViolation) as exc:
        r.check_status_change(OPEN, 9, False, FLOW, ALL)
    assert exc.value.code == "status_invalid"
    assert "[1, 2, 3, 4, 5]" in exc.value.message


def test_ut22_check_status_change_open_dependencies():
    with pytest.raises(RuleViolation) as exc:
        r.check_status_change(OPEN, RESOLVED, True, FLOW, ALL)
    assert exc.value.code == "dependencies_open"
    assert "resolve those first" in exc.value.message


def test_ut23_check_status_change_disallowed_transition_lists_allowed():
    with pytest.raises(RuleViolation) as exc:
        r.check_status_change(CLOSED, RESOLVED, False, FLOW, ALL)
    assert exc.value.code == "transition_not_allowed"
    assert exc.value.message == (
        "A ticket cannot move from status 4 to 3: allowed statuses are [2, 4]."
    )


def test_ut24_rule_violation_is_value_error_with_message():
    err = RuleViolation("x", "fix it")
    assert isinstance(err, ValueError)
    assert str(err) == "fix it"
    assert (err.code, err.message) == ("x", "fix it")


# ------------------------------------------------- BR-4 role access: MCC (8 rows)
@pytest.mark.parametrize(
    "auth, active, staff, expected",
    [
        (True, True, True, True),
        (True, True, False, False),
        (True, False, True, False),
        (True, False, False, False),
        (False, True, True, False),
        (False, True, False, False),
        (False, False, True, False),
        (False, False, False, False),
    ],
)
def test_ut25_br4_staff_api_access_mcc(auth, active, staff, expected):
    assert bool(r.can_use_staff_api(auth, active, staff)) is expected


# ---------------------------------------------- added after mutation analysis
# UT26-UT28 kill the killable survivors listed in docs/team/MUTATION.md.
def test_ut26_exact_messages_title_and_dependencies():
    """Kills mutmut validate_title_5/10/11/12 and check_status_change_18:
    the message text is what the submitter reads, so it is pinned exactly."""
    with pytest.raises(RuleViolation) as exc:
        r.validate_title("   ")
    assert exc.value.message == "Enter a summary of the problem."
    with pytest.raises(RuleViolation) as exc:
        r.check_status_change(OPEN, RESOLVED, True, FLOW, ALL)
    assert exc.value.message == (
        "This ticket depends on tickets that are still open: resolve "
        "those first, then change this ticket's status."
    )


def test_ut27_unknown_status_is_never_allowed_even_if_unchanged():
    """Kills custom GDO C06 (guard `new not in all_statuses` deleted):
    a ticket holding a status that is no longer configured cannot 'keep' it."""
    assert r.is_transition_allowed(99, 99, FLOW, ALL) is False


def test_ut28_unchanged_status_allowed_even_if_flow_omits_it():
    """Kills custom GDO C07 (guard `new == current` deleted): with a custom
    flow that does not list a status as its own successor, keeping the status
    (e.g. adding a comment) must still be allowed."""
    custom = {OPEN: (RESOLVED,), RESOLVED: (CLOSED,)}
    assert r.is_transition_allowed(OPEN, OPEN, custom, ALL) is True
    assert r.is_transition_allowed(OPEN, CLOSED, custom, ALL) is False
