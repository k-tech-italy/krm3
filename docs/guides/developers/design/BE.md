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
