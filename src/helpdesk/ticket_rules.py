"""Business rules for the two ticket workflows (SE3002 team module).

BR-1  Priority and title limits (boundary rule)
BR-2  Submitter status-change decision (three Boolean conditions)
BR-3  Ticket status lifecycle (change-of-state rule)
BR-4  Role-based access to the staff ticket API

The functions are pure: they import nothing from Django, so they can be unit
tested and mutation tested in isolation. Callers pass in the configured status
flow (``Ticket.STATUS_CHOICES_FLOW``) and the valid status codes.
"""

PRIORITY_MIN = 1
PRIORITY_MAX = 5
TITLE_MAX_LENGTH = 200


class RuleViolation(ValueError):
    """A business rule rejected a value. ``message`` says what to correct."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


# --------------------------------------------------------------------------- #
# BR-1  Boundary rules
# --------------------------------------------------------------------------- #
def validate_priority(value):
    """Return ``value`` as an int if it is a whole number from 1 to 5.

    Accepts ints and numeric strings ("3"). Rejects booleans, fractions,
    non-numeric values and anything outside PRIORITY_MIN..PRIORITY_MAX.
    """
    if isinstance(value, bool) or isinstance(value, float):
        raise RuleViolation(
            "priority_type",
            f"Priority must be a whole number from {PRIORITY_MIN} to {PRIORITY_MAX}.",
        )
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise RuleViolation(
            "priority_type",
            f"Priority must be a whole number from {PRIORITY_MIN} to {PRIORITY_MAX}.",
        ) from None
    if number < PRIORITY_MIN or number > PRIORITY_MAX:
        raise RuleViolation(
            "priority_range",
            f"Priority {number} is out of range: choose a value from "
            f"{PRIORITY_MIN} (Critical) to {PRIORITY_MAX} (Very Low).",
        )
    return number


def validate_title(title):
    """Return the stripped title if it is non-empty and at most 200 characters."""
    if not isinstance(title, str) or not title.strip():
        raise RuleViolation("title_required", "Enter a summary of the problem.")
    if len(title) > TITLE_MAX_LENGTH:
        raise RuleViolation(
            "title_too_long",
            f"The summary has {len(title)} characters: shorten it to "
            f"{TITLE_MAX_LENGTH} characters or fewer.",
        )
    return title.strip()


# --------------------------------------------------------------------------- #
# BR-3  Status lifecycle
# --------------------------------------------------------------------------- #
def allowed_next_statuses(current, flow, all_statuses):
    """Statuses reachable from ``current``.

    Mirrors ``Ticket._get_allowed_status_flow``: a status missing from the
    flow (or mapped to an empty tuple) may move to any valid status.
    """
    targets = flow.get(current, ())
    if targets:
        return tuple(targets)
    return tuple(all_statuses)


def is_transition_allowed(current, new, flow, all_statuses):
    """True if a ticket in ``current`` may move to ``new``."""
    if new not in all_statuses:
        return False
    if new == current:
        return True
    return new in allowed_next_statuses(current, flow, all_statuses)


# --------------------------------------------------------------------------- #
# BR-2  Submitter status-change decision (critical module for MCC / MC-DC)
# --------------------------------------------------------------------------- #
def submitter_may_change_status(current, new, has_open_dependencies, flow, all_statuses):
    """Decision used by the submitter's ticket page.

    Accept if (A) the ticket has no open dependencies OR (B) the status is
    unchanged, AND (C) the new status is allowed from the current one.

        decision = (not has_open_dependencies or new == current) and C
    """
    return (not has_open_dependencies or new == current) and is_transition_allowed(
        current, new, flow, all_statuses
    )


def check_status_change(current, new, has_open_dependencies, flow, all_statuses):
    """Raise RuleViolation explaining why a status change is not allowed.

    Applies BR-2 and BR-3 to every write path (submitter page, staff API).
    Returns ``new`` when the change is allowed.
    """
    if new not in all_statuses:
        raise RuleViolation(
            "status_invalid",
            f"Status {new} does not exist: use one of {sorted(all_statuses)}.",
        )
    if new != current and has_open_dependencies:
        raise RuleViolation(
            "dependencies_open",
            "This ticket depends on tickets that are still open: resolve "
            "those first, then change this ticket's status.",
        )
    if not is_transition_allowed(current, new, flow, all_statuses):
        allowed = sorted(set(allowed_next_statuses(current, flow, all_statuses)) | {current})
        raise RuleViolation(
            "transition_not_allowed",
            f"A ticket cannot move from status {current} to {new}: "
            f"allowed statuses are {allowed}.",
        )
    return new


# --------------------------------------------------------------------------- #
# BR-4  Role-based access
# --------------------------------------------------------------------------- #
def can_use_staff_api(is_authenticated, is_active, is_staff):
    """Only an authenticated, active staff account may use the ticket API."""
    return is_authenticated and is_active and is_staff
