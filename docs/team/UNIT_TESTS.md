# Unit Testing (White Box)

**Module under test:** [`src/helpdesk/ticket_rules.py`](../../src/helpdesk/ticket_rules.py),
the team's business-rule module. It is pure (no Django imports), and after the
fixes it is used by every write path: public view, API serializers and the
staff form. Tests: [`tests/team/unit/test_ticket_rules.py`](../../tests/team/unit/test_ticket_rules.py),
UT-00 to UT-28 (91 test cases).

## 1. Coverage

| File | Statements | Missed | Branches | Partial | Statement | Branch |
|---|---|---|---|---|---|---|
| `ticket_rules.py` | 48 | 0 | 20 | 0 | **100 %** | **100 %** |
| `tests/team/datagen/generate.py` (generator) | 156 | 0 | 68 | 0 | **100 %** | **100 %** |

Evidence: `evidence/regression/coverage_gate_final.txt`. CI fails if either
drops below 100 % (`unit-api-tests` job).

## 2. Test design per rule

| Tests | Rule | Technique | Cases |
|---|---|---|---|
| UT-00 | guard | the flow table used by the tests equals the application's `DEFAULT_TICKET_STATUS_CHOICES_FLOW` | 1 |
| UT-01 | BR-1 priority valid | EP valid class + BVA 1, 2, 4, 5 + numeric strings | 8 |
| UT-02 | BR-1 priority out of range | BVA 0, 6 (min−1, max+1), EP −1, 100 | 6 |
| UT-03 | BR-1 priority wrong type | EP: bool, float, text, empty, None, list | 8 |
| UT-04 | BR-1 limits | constants 1 and 5 and their messages | 1 |
| UT-05..UT-08 | BR-1 title | BVA 1, 199, 200 valid; 201 rejected with the character count; EP empty, blank, None, number; stripping | 9 |
| UT-09, UT-10 | BR-3 flow | every allowed (10) and disallowed (10) change of state | 20 |
| UT-11..UT-16 | BR-3 edge cases | stay in place (5 statuses), unknown targets (3), next-status list, unmapped status, empty mapping, counts | 12 |
| UT-17 | BR-2 decision | **MCC** (all feasible combinations) | 6 |
| UT-18 | BR-2 decision | **MC/DC** independence pairs | 3 |
| UT-19..UT-24 | BR-2 + BR-3 on all write paths (`check_status_change`) | basis paths of the CFG, error codes and messages | 6 |
| UT-25 | BR-4 access | **MCC**, all 8 combinations of authenticated × active × staff | 8 |
| UT-26..UT-28 | added after mutation analysis | exact messages; unknown status kept; custom flow without self-loops | 3 |

## 3. State-transition table (BR-3)

| From \ To | Open | Reopened | Resolved | Closed | Duplicate |
|---|---|---|---|---|---|
| **Open** | stay | ✗ | ✓ | ✓ | ✓ |
| **Reopened** | ✗ | stay | ✓ | ✓ | ✓ |
| **Resolved** | ✗ | ✓ | stay | ✓ | ✗ |
| **Closed** | ✗ | ✓ | ✗ | stay | ✗ |
| **Duplicate** | ✗ | ✓ | ✗ | ✗ | stay |

10 valid (✓) and 10 invalid (✗) changes, all tested at unit level (UT-09/10),
API level through follow-ups and PATCH (`test_state_transitions.py`, 44 cases)
and in the browser (UC-3, UC-4).

## 4. MCC and MC/DC for BR-2 (critical module)

Decision used by the submitter page and `check_status_change`:

    decision = (A or B) and C
    A = the ticket has no open dependencies
    B = the new status equals the current status
    C = the change is allowed by the status flow

### 4.1 Multiple Condition Coverage

| Row | A | B | C | Decision | Test input (deps, current → new) |
|---|---|---|---|---|---|
| M1 | T | F | T | **T** | no deps, Open → Resolved |
| M2 | T | F | F | **F** | no deps, Closed → Resolved |
| M3 | T | T | T | **T** | no deps, Open → Open |
| M4 | T | T | F | – | **infeasible**: B = T forces C = T (staying put is always allowed) |
| M5 | F | F | T | **F** | deps open, Open → Resolved |
| M6 | F | F | F | **F** | deps open, Closed → Resolved |
| M7 | F | T | T | **T** | deps open, Open → Open |
| M8 | F | T | F | – | **infeasible** (same reason as M4) |

All **6 feasible** combinations are tested (UT-17). The test first asserts that
each input really produces the intended values of A, B and C, then the outcome.

### 4.2 Modified Condition/Decision Coverage

| Condition | Pair | Held fixed | Outcome flips |
|---|---|---|---|
| A | M1 / M5 | B = F, C = T | T → F |
| B | M5 / M7 | A = F, C = T | F → T |
| C | M1 / M2 | A = T, B = F | T → F |

Minimum MC/DC set: **{M1, M2, M5, M7}**, n + 1 = 4 tests for 3 conditions.
UT-18 checks programmatically that each pair differs in exactly one condition
and that the outcome changes.

The same decision table (rows R1 to R4) is also tested end to end on the
submitter's ticket page (`tests/team/api/test_decision_br2.py`: R1, R1b, R2,
R3, R4, R4b → 302 accept / 403 reject) and on the staff form
(`test_staff_form_rules.py`).

## 5. MCC for BR-4

`can_use_staff_api = authenticated and active and staff`: all 8 combinations
(UT-25). Only (T, T, T) grants access. The API permission class
`IsActiveStaffUser` uses this function, and `test_access_br4.py` checks the
real endpoints (anonymous, customer, inactive staff, staff).
