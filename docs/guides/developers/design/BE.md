# Backend Design Decisions

### DDR-BE-001: DTO Pattern for Complex Responses
- **Date**: 2026-08-03
- **Context**: Timesheet responses aggregate data from many models, and assembling them inside views or serializers mixed data transformation with API logic.
- **Decision**: The timesheet module uses a DTO (Data Transfer Object) pattern (`TimesheetDTO`) to assemble complex response data in dedicated classes.
- **Consequences**: Data transformation is separated from API logic and independently testable; adds an extra layer to maintain alongside serializers.
- **Status**: Accepted

### DDR-BE-002: Lightweight Event System
- **Date**: 2026-08-03
- **Context**: Decoupled modules need to react to domain events without pulling in a full message broker or Django signals spaghetti.
- **Decision**: A custom pub/sub event dispatcher (`krm3.events`) with pluggable backends, defaulting to `NullEventDispatcherBackend` in tests.
- **Consequences**: The event system is testable and swappable; being custom, it must be documented and maintained in-house rather than relying on a third-party library.
- **Status**: Accepted

### DDR-BE-003: Row-Level Access Control via `filter_acl` Manager Method
- **Date**: 2026-08-03
- **Context**: Many models (Mission, Expense, Project, Task, DayEntry, Contract, …) must restrict which records a given user can see, and ad-hoc filtering in views leads to inconsistent and easily forgotten access checks.
- **Decision**: When checking which records are accessible by a user, use the `filter_acl(user)` model manager/queryset method. Each model's manager encapsulates its own row-level ACL rules, and views/DTOs call `Model.objects.filter_acl(user)` instead of building permission filters inline.
- **Consequences**: Access rules live in one place per model and are consistently applied across API views, admin, and DTOs; every new model exposing user-scoped data must implement `filter_acl` on its manager.
- **Status**: Accepted

### DDR-BE-004: Meaningful `id` Kwarg for `pytest.param`
- **Date**: 2026-08-03
- **Context**: Parametrized tests without explicit ids produce auto-generated names (e.g. `test_foo[param0]`) that make it hard to tell which case failed or to select a single case with `-k`.
- **Decision**: Whenever using `pytest.param`, always pass a meaningful `id` kwarg describing the scenario being tested.
- **Consequences**: Test output and failure reports are self-explanatory and individual cases are easy to target; writing parametrized tests requires slightly more effort to name each case.
- **Status**: Accepted

### DDR-BE-005: Frozen Bank Balance in Closed Timesheets
- **Date**: 2026-10-20
- **Context**: Validating a Bank of Hours transaction and freezing a timesheet both need the resource bank balance up to a given day. Re-summing every day entry on every call gets slower as the history grows, and the timesheet snapshot already stores a `bank_hours` key whose value used to be computed at a different date boundary than the balance queries expected.
- **Decision**: `Resource.get_bank_hours_balance(at, use_watermark=True)` rebuilds the balance from the `bank_hours` value frozen in the most recent closed timesheet whose period ends at or before `at`, then adds the entries logged after it. The frozen value is authoritative regardless of earlier open or missing timesheets and represents the balance as of the last day of the period. A timesheet cannot be created, reopened, modified or deleted while a later closed timesheet exists for the same resource, and neither can its related DayEntry and TaskEntry records be modified. The Bank of Hours limits validator checks the running balance from the earliest affected day forward, and only when the transaction changes the balance or the day.
- **Consequences**: Balance reads stay proportional to the entries after the last closed timesheet instead of the whole history, and incomplete history before that snapshot is ignored. Correcting an earlier period requires reopening later submissions in reverse chronological order and closing them again in chronological order, so each snapshot is rebuilt from the previous authoritative balance. When no closed snapshot containing `bank_hours` exists, the balance falls back to the full DayEntry sum.
- **Status**: Accepted

### DDR-BE-006: Mandatory Monthly Timesheet Order
- **Date**: 2026-10-21
- **Context**: Bank balance snapshots depend on previous closed timesheets, but historical data contains missing submissions that must remain unchanged.
- **Decision**: A resource's first closed timesheet establishes its starting point. Every later timesheet must be submitted in chronological monthly order for months covered by an active contract. Months without an active contract are skipped, and missing submissions before the latest closed timesheet are not validated retroactively.
- **Consequences**: New gaps cannot be introduced after the starting point, while existing historical gaps remain untouched. Closing a timesheet fails when an earlier contracted month after the latest closed submission is still open or missing.
- **Status**: Accepted
