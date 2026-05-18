# Key Design Choices

## State Management: React Query Only

No Redux, MobX, or Zustand. All server state is managed via **TanStack Query** (`useQuery`/`useMutation`). Client state stays in React local state or minimal Context (auth, language). This keeps the frontend simple and avoids unnecessary abstraction.

## CamelCase API Convention

Despite Django's native snake_case, all API uses **camelCase**. The backend uses `djangorestframework-camel-case` for automatic conversion; the frontend uses `axios-case-converter`. This gives idiomatic JS on the client while keeping Python conventions on the server.

## Session Auth (No JWTs)

Authentication uses **Django session cookies** with CSRF protection, backed by social-auth-app-django or username/password. No JWTs, no token refresh complexity. The SPA and API share the same session.

## Tailwind CSS v4 + Dark Mode

The frontend uses **Tailwind v4** with CSS custom properties for theming. Dark/light mode is managed via `next-themes` with `class` strategy. Brand colors use custom `krm3-*` utility classes.

## Feature Flags via django-flags

Module-level gating (timesheet, missions, expenses) is controlled by **django-flags**, checked both API-side and UI-side. No branch-based feature toggling.

## DTO Pattern for Complex Responses

The timesheet module uses a **DTO (Data Transfer Object)** pattern (`TimesheetDTO`) to assemble complex response data in dedicated classes rather than in views or serializers, separating data transformation from API logic.

## Lightweight Event System

Custom pub/sub event dispatcher (`krm3.events`) with pluggable backends. Defaults to `NullEventDispatcherBackend` in tests, making the event system testable and swappable.
