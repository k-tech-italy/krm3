# Key Development Choices

## Monorepo with Independent Frontend

The backend (Django 5.2, Python ≥3.12) and frontend (React 18 SPA, TypeScript) live in the same repo. The frontend is a **git submodule** pointing to a separate repository, built independently with Vite 7 and served by Django (dev) or nginx (prod). This avoids CORS issues and allows independent versioning/CI for each side.

## uv for Python Package Management

Uses **uv** (Astral's Rust-based tool) for fast dependency resolution and reproducible builds via `uv.lock`.

## Docker + Rancher Deployment

Single multi-stage Docker image (uWSGI + nginx + Circus process manager). Deployed via **Rancher** with GitHub Actions workflows for test, deploy (master), and prod-deploy (manual). Entrypoint handles migrations, static/media setup, and nginx config generation.

## Conventional Commits + Semantic Versioning

`commitizen` enforces conventional commits. Version bumps and changelog generation follow PEP 440 semver. Version is coordinated between `pyproject.toml` and `src/krm3/__init__.py`.

## Testing Strategy

- **Backend**: pytest with `pytest-django`, `pytest-xdist`, tox. Tests organized as unit/integration (Selenium)/API.
- **Frontend**: Vitest with `@testing-library/react`, co-located `.test.tsx` files.
- **Linting**: Ruff (Python) and ESLint + Prettier (frontend), enforced via pre-commit hooks and CI.
- **Type checking**: pyright/pyrefly (Python), TypeScript strict (frontend).
