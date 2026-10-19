# AGENTS.md

Guidance for AI coding agents working on KRM3. Humans should start from
[README.md](README.md) and [CONTRIBUTING.md](CONTRIBUTING.md); this file adds what an agent needs
to work safely and match the existing code.

## Project

KRM3 is K-Tech's resource management platform: timesheets, missions and expense reimbursements,
contracts, projects, documents, currencies and contacts.

- Backend: Django 5.2 + Django REST Framework, Python 3.12, PostgreSQL. Managed with `uv`.
- Frontend: React + TypeScript + Vite + Tailwind v4, in the **`krm3-fe/` git submodule**
  (separate repo: `k-tech-italy/krm3-fe`). Managed with `yarn`.
- Docs: MkDocs under `docs/` (glossary, user and developer guides, design decisions).

## Layout

| Path | Contents |
|---|---|
| `src/krm3/core/models/*.py` | **Almost all domain models** (missions, expenses, reimbursements, timesheets, contracts, projects, auth, ...). App label `core`; their migrations are in `src/krm3/core/migrations/` |
| `src/krm3/<app>/` | Feature apps (`missions`, `timesheet`, `currencies`, `documents`, `accounting`, `projects`, `web`, `fe`, ...): admin, API, forms, views, templates. Most have no models of their own |
| `src/krm3/api/urls.py` | Mounts each app's DRF routers under `/api/v1/` |
| `src/krm3/config/` | Settings (`settings.py` + `fragments/`), URLs, env handling (`environ.py`, defaults in `__init__.py` `DEFAULTS`) |
| `src/krm3/core/api/permissions.py` | Shared DRF permissions (`FeatureFlagEnabled`, `IsOwnerOrManager`, ...) |
| `tests/` | pytest suite: `unit/`, `api/`, `integration/` (Selenium); factories in `tests/_extras/testutils/factories/` |
| `docs/` | MkDocs site; design decisions in `docs/guides/developers/design/` |
| `krm3-fe/` | Frontend submodule |

## Commands

Backend (from the repo root; needs a reachable PostgreSQL in `KRM3_DATABASE_URL`, see `.env.example`):

```bash
uv sync                                   # install/refresh dependencies
uv run pytest tests/unit/missions         # run part of the suite (selenium excluded by default)
uv run pytest tests/unit tests/integration/foundations   # broader non-browser run
uv run ruff check <paths>                 # lint
uv run ruff format --check <paths>        # format check
uv run ./manage.py makemigrations --check --dry-run      # pending migrations?
tox -e docs                               # build the MkDocs site (must pass for doc changes)
tox                                       # lint + full tests + docs + package checks, as in CI
make lint                                 # pre-commit run --all-files
```

Frontend (inside `krm3-fe/`):

```bash
yarn install
npx tsc --noEmit -p .        # type check
npx vitest run               # tests (yarn test starts watch mode)
npx eslint <files>           # lint
npx prettier --check <files>
```

## Conventions that matter

Read the design decisions in `docs/guides/developers/design/` (`Global.md`, `BE.md`, `FE.md`)
before changing behaviour. The ones most often relevant:

- **API payloads are camelCase** (DDR-G-001): `djangorestframework-camel-case` converts on the
  backend, so tests post `fromDate`, not `from_date`.
- **Session auth, no JWT** (DDR-G-002).
- **Feature flags** (DDR-G-003): modules are gated by django-flags (`src/krm3/config/fragments/flags.py`),
  **both** in the UI and in the API. API viewsets add `FeatureFlagEnabled` and set `feature_flag`
  (missions use `TRASFERTE_ENABLED`).
- **Row-level access** (DDR-BE-003): querysets go through `Model.objects.filter_acl(user)`;
  never filter by permissions inline in views.
- **Permissions use the `core.` app label** (`core.view_any_mission`, `core.manage_any_mission`,
  `core.add_mission`, ...), because the models live in `core`. `missions.*` names never match.
- **View vs manage**: `view_any_*` is read-only; modifying other resources' records requires
  `manage_any_*` (`IsOwnerOrManager`, set `owner_field` and `manage_permission` on the viewset).
- Models that call `full_clean()` in `save()` raise Django `ValidationError`; in DRF serializers
  convert it to `serializers.ValidationError` so the API answers 400, not 500.
- Ruff: line length 120, single quotes, annotations required (see `ruff.toml`). Match the
  surrounding code's style and comment density.

### Domain rules to preserve

The glossary (`docs/glossary/terms/`) documents business rules; keep code and glossary in sync
when either changes. Examples:

- Missions are created in DRAFT without a number; the number is assigned on submission
  (`Mission.submit()`), per year, restarting from 1.
- Reimbursements are created **only** by the *Create reimbursement* expense admin action; the
  Reimbursement admin has no add view.
- `Expense.amount_reimbursement` sign/amount depends on `PaymentCategory.personal_expense` and
  the receipt image (see `docs/glossary/terms/Expense.md`).

## Tests

- pytest style only (functions/classes, fixtures, plain asserts). Use factories from
  `testutils.factories` and global fixtures from `tests/conftest.py` (`regular_user`,
  `admin_user`, `resource`, `api_client(user=...)`, ...). `pytest.ini` adds `--reuse-db` and
  excludes `selenium` tests.
- Parametrize with `pytest.param(..., id='meaningful-id')` (DDR-BE-004).
- Permission changes need a matrix test (no permission / view-only / manager / owner).
- When fixing a bug, check that the new test fails on the old code.
- **Do not modify or delete existing tests without the user's approval.** Adding new tests is fine.
- Factories must not rely on model side effects you remove (e.g. `ReimbursementFactory` sets
  `number` explicitly).

## Docs

- Glossary terms are linked with `<glossary:Term>` (mkdocs-ezglossary).
- Prefer ASCII in pages: the `include-markdown` plugin reads included files as ASCII.
- New design decisions go in `docs/guides/developers/design/` as `DDR-<scope>-NNN` entries.
- Always run `tox -e docs` after doc changes.

## Frontend submodule (`krm3-fe/`)

- Changes are committed and pushed in the submodule repo, with their own branch and PR.
  Bump the submodule pointer in this repo only when asked.
- Permission checks in the UI use `useGetCurrentUser().userCan(['core.<perm>'])`
  (superusers always pass). Mirror every UI restriction in the backend.
- Its pre-commit hook runs `prettier --write` and `yarn lint` on staged files. Many existing
  files already have ESLint errors, so the hook may fail on code you did not touch. Do not add
  new lint problems; ask the user before committing with `--no-verify`.
- Dark mode: native controls depend on `color-scheme` and the theme variables in `src/index.css`.

## Git, PRs and tickets

- Branch from and open PRs against `develop`. Branch names: `<type>/<ticket>-short-description`
  with `<type>` one of `feat`, `fix`, `bug`, `docs`, `refactor`, `test`, `style`, `chore`
  (see CONTRIBUTING.md).
- Conventional Commits (`fix(missions): ...`, `feat: ...`, `docs: ...`), enforced by the
  commitizen hook. Do not bump versions or edit `CHANGELOG.md`; the release manager does it.
- Pre-commit hooks include ruff, `check-missed-migrations` and `check-forbidden` (no
  `.showbrowser(`). Never commit `.env` files or secrets.
- Only commit, push, open PRs or update tickets when the user asks. Stage files explicitly; do
  not include an unrelated `krm3-fe` pointer change.
- Tickets live in Taiga (project `krm3`); reference them in commits as `Refs: taiga#<ref>`.
  Describe security issues by class of problem, without step-by-step exploit instructions.

## Don'ts

- Don't reformat whole files you are not otherwise changing (many files predate the current
  ruff/prettier settings); keep diffs focused.
- Don't hand-edit migrations that are already merged; generate new ones with `makemigrations`.
- Don't run destructive git commands (`checkout -- .`, `reset --hard`, force push) without
  confirming; prefer `--force-with-lease` when a rebase has to be pushed.
