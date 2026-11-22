# Test Scope and Test Basis

## 1. System under test

django-helpdesk at baseline commit `7bf832c` (see [BASELINE.md](BASELINE.md)).
**Module under test:** Ticket Management (`src/helpdesk/`).

## 2. Workflows

| | Workflow 1: Submit Ticket | Workflow 2: Update / Resolve Ticket |
|---|---|---|
| **Starting condition** | A queue exists that accepts submissions. No ticket exists for the request. | A ticket created by Workflow 1 exists with status Open (1). |
| **User action** | A submitter fills in the public form at `/tickets/submit/` (queue, title, description, email, priority). A staff member can create the same ticket with `POST /api/tickets/`. | A staff member adds a follow-up with a new status (`/tickets/<id>/update/` or `POST /api/followups/`). A submitter can comment on or change the status of their own ticket at `/view/`. |
| **Expected outcome** | The ticket is saved with status **Open (1)**, the given priority, a ticket ID, and a secret key for the submitter. It appears in the staff ticket list and in `GET /api/tickets/`. | A follow-up record is saved. The ticket status changes when the transition is allowed. A disallowed transition, or resolving a ticket with open dependencies, is rejected and the status stays unchanged. |

### Shared record

**`Ticket`** (table `helpdesk_ticket`), especially the field **`status`**.

| Workflow | Reads | Changes |
|---|---|---|
| W1 Submit | `Queue` (must exist, must be accessible) | Creates `Ticket` (`status=1`, `priority`, `title`, `submitter_email`, `secret_key`) |
| W2 Update | `Ticket.status`, `Ticket.secret_key`, `TicketDependency` (open dependencies) | `Ticket.status`, `Ticket.assigned_to`, `Ticket.priority`; creates `FollowUp` (with `new_status`) and `TicketChange` |

W1 sets the status that W2 reads, so W2's allowed transitions depend directly on W1's output.

## 3. User roles

| Role | Django account | Permissions |
|---|---|---|
| **Staff agent** | `is_staff=True` | Staff UI (`/tickets/...`), all ticket and follow-up API endpoints (`IsAdminUser`), any status change, assign, re-prioritise. |
| **Submitter** | No account, or `is_staff=False` | Submits tickets on the public form. Views and updates **only their own** ticket, using email + secret key. Status changes limited by the flow table. Gets **403** on `/api/tickets/` and `/api/followups/`. Can list own tickets on `/api/user_tickets/` (matched by non-empty email). |

`HELPDESK_ALLOW_NON_STAFF_TICKET_UPDATE` is `False` in the demo settings (the default),
so the roles stay separate.

## 4. Functional requirements

| ID | Workflow | Requirement | Source |
|---|---|---|---|
| FR-01 | W1 | The system shall create a ticket from the public form when queue, title, description and a valid email are given. | `views/public.py` `create_ticket`, docs |
| FR-02 | W1 | A new ticket shall always start with status **Open (1)**, even if another status is sent. | `docs/api.rst` ("status will automatically be set to OPEN") |
| FR-03 | W1 | Priority shall be an integer from 1 (Critical) to 5 (Very Low), with default 3 (Normal). | `settings.py` `DEFAULT_TICKET_PRIORITY_CHOICES`, `models.py` |
| FR-04 | W1 | Title is required, maximum 200 characters. Submitter email must be a valid email. | `models.py` `Ticket.title max_length=200`, `EmailField` |
| FR-05 | W1 | A staff user shall be able to create a ticket with `POST /api/tickets/` and receive `201` with the ticket ID. Non-staff receive `403`. | `views/api.py` `TicketViewSet` (`IsAdminUser`), `docs/api.rst` |
| FR-06 | W2 | A staff user shall be able to change a ticket's status by adding a follow-up (`POST /api/followups/` with `new_status`). A `FollowUp` record is saved. | `serializers.py` `FollowUpSerializer.create`, `update_ticket.py` |
| FR-07 | W2 | A status change shall only be accepted if it is allowed from the current status by the status flow table. | `settings.py` `DEFAULT_TICKET_STATUS_CHOICES_FLOW`, `views/public.py` |
| FR-08 | W2 | A ticket with open dependencies shall not change status (in particular, cannot be resolved). | `models.py` `can_be_resolved`, `views/public.py` |
| FR-09 | W2 | A submitter shall only access their own ticket. A wrong email or secret key is denied (`403`). | `views/public.py` (`PermissionDenied`) |
| FR-10 | W2 | Each status change shall be recorded in the ticket history (`FollowUp.new_status`, title "Resolved" etc.). | `update_ticket.py` `get_and_set_ticket_status` |

## 5. Business rules

### BR-1 Priority boundary (boundary / limit)
`priority` ∈ {1, 2, 3, 4, 5}. Values outside 1–5 are rejected.
BVA points: **0, 1, 2** (lower) and **4, 5, 6** (upper).
A second boundary on the same form: `title` length **199, 200, 201** characters.

### BR-2 Submitter status change (decision, three Boolean conditions)
Source: `views/public.py` `update_ticket_from_public_view` (approx. lines 241–254).

A submitter's update is **accepted** only if:

> **C1** the ticket has no open dependencies (`can_be_resolved`) **OR** **C2** the status is unchanged,
> **AND** **C3** the new status is in the allowed set for the current status (or equals it).

Decision table:

| Rule | C1 no open deps | C2 status unchanged | C3 in allowed flow | Outcome |
|---|---|---|---|---|
| R1 | T | – | T | Accept |
| R2 | T | – | F | Reject 403 |
| R3 | F | T | T | Accept (comment only) |
| R4 | F | F | – | Reject 403 |

(C2 = T implies C3 = T, since the current status is always allowed.)

### BR-3 Ticket status lifecycle (change of state)
Source: `settings.py` `DEFAULT_TICKET_STATUS_CHOICES_FLOW`.

| From \ To | Open (1) | Reopened (2) | Resolved (3) | Closed (4) | Duplicate (5) |
|---|---|---|---|---|---|
| **Open (1)** | stay | ✗ | ✓ | ✓ | ✓ |
| **Reopened (2)** | ✗ | stay | ✓ | ✓ | ✓ |
| **Resolved (3)** | ✗ | ✓ | stay | ✓ | ✗ |
| **Closed (4)** | ✗ | ✓ | ✗ | stay | ✗ |
| **Duplicate (5)** | ✗ | ✓ | ✗ | ✗ | stay |

Initial state: Open. The ✗ cells are the disallowed transitions used in state-transition testing.

### BR-4 Role-based access (permission)
- Ticket and follow-up API endpoints require `is_staff=True`. Anonymous users get **401/403**; non-staff get **403**.
- A non-staff user's `/api/user_tickets/` returns only tickets whose `submitter_email` equals the user's **non-empty** email.
- A submitter can open `/view/` only with the matching email **and** secret key.

## 6. Test basis and justified assumptions

| # | Assumption | Justification |
|---|---|---|
| A1 | BR-3 (status flow) **should** apply to every path that changes status, including the staff UI, `POST /api/followups/` and the Kanban endpoint. | It's the only documented lifecycle, and the public view enforces it. At baseline, `FollowUpSerializer.create` and `kanban_update_ticket` pass `new_status` without checking the flow or `can_be_resolved`. **This is treated as a defect candidate** (endpoint weakness). |
| A2 | `POST /api/tickets/` with `status≠1` should still produce an Open ticket. | Stated in `docs/api.rst`. Verified by API tests. |
| A3 | A repeated identical `POST` (same follow-up sent twice) should not create a second status change. | Idempotency expectation for the "no duplicates" requirement. Verified by API tests. |
| A4 | Email notifications are out of scope. The email backend is the console/locmem backend. | No external mail server in the test environment. |

## 7. Business-logic scope for unit testing (100% statement + branch)

| Unit | File |
|---|---|
| `Ticket._get_allowed_status_flow`, `Ticket.can_be_resolved`, `Ticket.get_status` | `src/helpdesk/models.py` |
| `get_and_set_ticket_status`, `get_email_template_prefix` | `src/helpdesk/update_ticket.py` |
| Status-change decision in `update_ticket_from_public_view` | `src/helpdesk/views/public.py` |
| `check_staff_status` / `is_helpdesk_staff` | `src/helpdesk/decorators.py` |
| Team business-rule module `ticket_rules.py` (BR-1 to BR-3, used to fix A1) | `src/helpdesk/ticket_rules.py` (added by team) |

**Critical module for MCC / MC-DC:** BR-2 (the submitter status-change decision).

## 8. Out of scope
Email polling (`email.py`), knowledge base, Kanban UI rendering, teams mode, webhooks,
attachments beyond a single valid upload, translations.
