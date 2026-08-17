# Frontend Design Decisions

### DDR-FE-001: State Management via React Query Only
- **Date**: 2026-08-03
- **Context**: A dedicated client-side store (Redux, MobX, Zustand) would add abstraction the app does not need, since almost all state is server state.
- **Decision**: All server state is managed via TanStack Query (`useQuery`/`useMutation`); client state stays in React local state or minimal Context (auth, language).
- **Consequences**: Simpler frontend with built-in caching and refetching; genuinely global client state must fit into Context or be lifted into server state.
- **Status**: Accepted

### DDR-FE-002: Tailwind CSS v4 with Dark Mode
- **Date**: 2026-08-03
- **Context**: The UI needs consistent theming with dark/light support and brand colors without a heavyweight component library.
- **Decision**: Use Tailwind v4 with CSS custom properties for theming; dark/light mode is managed via `next-themes` with the `class` strategy, and brand colors use custom `krm3-*` utility classes.
- **Consequences**: Theming is centralized in CSS variables and utilities; contributors must use the `krm3-*` classes rather than hard-coding colors to keep both themes working.
- **Status**: Accepted
