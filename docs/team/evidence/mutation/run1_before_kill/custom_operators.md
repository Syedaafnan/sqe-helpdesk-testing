| ID | Operator | Variant | Function | Line | Mutated code | Status |
|---|---|---|---|---|---|---|
| C01 | GDO | delete-guard | validate_priority | 36 | `pass` | killed |
| C02 | GDO | delete-guard | validate_priority | 48 | `pass` | killed |
| C03 | GDO | delete-guard | validate_title | 59 | `pass` | killed |
| C04 | GDO | delete-guard | validate_title | 61 | `pass` | killed |
| C05 | GDO | delete-guard | allowed_next_statuses | 80 | `pass` | killed |
| C06 | GDO | delete-guard | is_transition_allowed | 87 | `pass` | survived |
| C07 | GDO | delete-guard | is_transition_allowed | 89 | `pass` | survived |
| C08 | GDO | delete-guard | check_status_change | 116 | `pass` | killed |
| C09 | GDO | delete-guard | check_status_change | 121 | `pass` | killed |
| C10 | GDO | drop-operand-0 | validate_priority | 36 | `if isinstance(value, float):` | killed |
| C11 | GDO | drop-operand-1 | validate_priority | 36 | `if isinstance(value, bool):` | killed |
| C12 | GDO | drop-operand-0 | validate_priority | 48 | `if number > PRIORITY_MAX:` | killed |
| C13 | GDO | drop-operand-1 | validate_priority | 48 | `if number < PRIORITY_MIN:` | killed |
| C14 | GDO | drop-operand-0 | validate_title | 59 | `if not title.strip():` | killed |
| C15 | GDO | drop-operand-1 | validate_title | 59 | `if not isinstance(title, str):` | killed |
| C16 | BSO | TITLE_MAX_LENGTH+1 | validate_title | 61 | `if len(title) > TITLE_MAX_LENGTH + 1:` | killed |
| C17 | BSO | TITLE_MAX_LENGTH-1 | validate_title | 61 | `if len(title) > TITLE_MAX_LENGTH - 1:` | killed |
| C18 | GDO | drop-operand-0 | submitter_may_change_status | 105 | `return is_transition_allowed(current, new, flow, all_statuses)` | killed |
| C19 | GDO | drop-operand-1 | submitter_may_change_status | 105 | `return not has_open_dependencies or new == current` | killed |
| C20 | GDO | drop-operand-0 | check_status_change | 121 | `if has_open_dependencies:` | killed |
| C21 | GDO | drop-operand-1 | check_status_change | 121 | `if new != current:` | killed |
| C22 | GDO | drop-operand-0 | can_use_staff_api | 142 | `return is_active and is_staff` | killed |
| C23 | GDO | drop-operand-1 | can_use_staff_api | 142 | `return is_authenticated and is_staff` | killed |
| C24 | GDO | drop-operand-2 | can_use_staff_api | 142 | `return is_authenticated and is_active` | killed |
| C25 | BSO | PRIORITY_MIN+1 | validate_priority | 48 | `if number < PRIORITY_MIN + 1 or number > PRIORITY_MAX:` | killed |
| C26 | BSO | PRIORITY_MIN-1 | validate_priority | 48 | `if number < PRIORITY_MIN - 1 or number > PRIORITY_MAX:` | killed |
| C27 | BSO | PRIORITY_MAX+1 | validate_priority | 48 | `if number < PRIORITY_MIN or number > PRIORITY_MAX + 1:` | killed |
| C28 | BSO | PRIORITY_MAX-1 | validate_priority | 48 | `if number < PRIORITY_MIN or number > PRIORITY_MAX - 1:` | killed |
| C29 | GDO | drop-operand-0 | submitter_may_change_status | 105 | `return new == current and is_transition_allowed(current, new, flow, all_statuses)` | killed |
| C30 | GDO | drop-operand-1 | submitter_may_change_status | 105 | `return not has_open_dependencies and is_transition_allowed(current, new, flow, all_statuses)` | killed |

BSO: 6/6 killed

GDO: 22/24 killed

Custom-operator mutation score = 28/30 = 93.3%
