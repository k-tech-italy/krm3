# Global Design Decisions (FE + BE)

### DDR-G-001: CamelCase API Convention
- **Date**: 2026-08-03
- **Context**: Django natively uses snake_case while idiomatic JavaScript uses camelCase, forcing one side to adopt foreign naming conventions.
- **Decision**: All API payloads use camelCase, with `djangorestframework-camel-case` converting automatically on the backend and `axios-case-converter` on the frontend.
- **Consequences**: Idiomatic code on both sides with no manual mapping; adds a conversion layer that must be kept in mind when debugging raw payloads.
- **Status**: Accepted

### DDR-G-002: Session Auth (No JWTs)
- **Date**: 2026-08-03
- **Context**: The SPA and the API are served from the same origin, so a token-based scheme would add complexity without benefit.
- **Decision**: Authentication uses Django session cookies with CSRF protection, backed by social-auth-app-django or username/password; the SPA and API share the same session.
- **Consequences**: No token refresh logic or JWT storage concerns; requires CSRF handling on mutating requests and ties clients to cookie-capable environments.
- **Status**: Accepted

### DDR-G-003: Feature Flags via django-flags
- **Date**: 2026-08-03
- **Context**: Modules (timesheet, missions and their expenses, report, contacts) need to be enabled per deployment without branch-based feature toggling.
- **Decision**: Module-level gating is controlled by django-flags, checked both API-side and UI-side. API-side, viewsets add the `krm3.core.api.permissions.FeatureFlagEnabled` permission and name the flag in a `feature_flag` attribute (e.g. the missions API uses `TRASFERTE_ENABLED`); when the flag is disabled for the request the API answers 403. UI-side, the frontend only exposes the modules listed in the current user's `config.modules`.
- **Consequences**: Features can be toggled per environment without code changes; every gated module must enforce the flag in both layers to stay consistent.
- **Status**: Accepted

Module flags (`src/krm3/config/fragments/flags.py`; the frontend entries come from
`LABEL_TO_FLAG_URL_MAP` in `src/krm3/core/api/serializers/user_serializer.py`):

| Flag | Module | Frontend URL | Notes |
|------|--------|--------------|-------|
| `TRASFERTE_ENABLED` | Missions, **including expenses** | `/trasferte` | *trasferte* is Italian for missions; expenses have no flag of their own. Off unless enabled |
| `TIMESHEET_ENABLED` | Timesheet | `/timesheet` | Off unless enabled |
| `REPORT_ENABLED` | Reports | `/be/` | On by default |
| `CONTACTS_ENABLED` | Contacts | `/contacts` | Off unless enabled |

Technical flags, not modules: `DDT_ENABLED` (Django Debug Toolbar), `EVENTS_ENABLED`
(event dispatching), `SQL_PERF_MONITOR_ENABLED` (SQL performance monitor, on when `DEBUG`).
