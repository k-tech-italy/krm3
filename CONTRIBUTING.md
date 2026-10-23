# Contributing to KRM3

Thank you for contributing to KRM3! This repository is public, so the instructions below are self-contained and do not require access to internal tools such as Docmost.

## Prerequisites

Set up your local environment as described in [README.md](./README.md): it lists the required
tools (UV, Ruff, PostgreSQL, Node.js and Yarn, Commitizen) and installs the git hooks.

## Branching

- Long-lived branches:
  - `develop`: integration branch — target all PRs here.
  - `master`: release branch — only maintainers merge release PRs here.
- Create your working branch from `develop`:

  ```bash
  git switch develop && git pull
  git switch -c fix/123-short-description
  ```

### Branch naming

Use `<type>/<ticket-number>-short-description`, where `<type>` is one of:

| Type | Use for |
|------|---------|
| `feat/` | new features |
| `fix/` | bug fixes |
| `bug/` | bug fixes (same as `fix/`) |
| `docs/` | documentation only |
| `refactor/` | code changes that neither fix a bug nor add a feature |
| `test/` | adding or fixing tests |
| `style/` | formatting, no code meaning change |
| `chore/` | maintenance, dependencies, build |

Example: `fix/685-remove-add-reimbursement`.

## Commits

KRM3 uses [Conventional Commits](https://www.conventionalcommits.org/) to drive the changelog and versioning:

| Type | Use for | SemVer bump |
|------|---------|-------------|
| `feat:` | new features | minor |
| `fix:` | bug fixes | patch |
| `docs:` | documentation only | none |
| `refactor:` | code changes that neither fix a bug nor add a feature | none |
| `test:` | adding or fixing tests | none |
| `style:` | formatting, no code meaning change | none |
| `chore:` | maintenance, dependencies, build | none |
| `BREAKING CHANGE:` (footer) or `!` after the type | incompatible changes | major |

An optional scope goes in brackets, e.g. `fix(missions): ...`. The `commit-msg` hook rejects
messages that do not follow the convention.

Commitizen (a prerequisite, see [README.md](./README.md#mandatory-requirements)), must be used to perform the commits, offers an
interactive prompt:

```bash
cz commit
```

Squash work-in-progress commits before merging if needed.

## Git hooks

`pre-commit install` (see [README.md](./README.md#preparation)) installs the `pre-commit`,
`commit-msg` and `pre-push` hooks from `.pre-commit-config.yaml`. They check, among other
things:

- on commit: Ruff, missing Django migrations, forbidden patterns (e.g. trailing whitespace
  and end-of-file fixes, compiled translations;
- on the commit message: the Conventional Commits format (Commitizen);
- on push: secrets (detect-secrets, against `.secrets.baseline`) and that no files under `src/`
  or `tests/` are left untracked.


Run all the commit-stage hooks on the whole tree with `make lint`.

## Running tests

The tests need the PostgreSQL server configured in `KRM3_DATABASE_URL` (pytest creates its own
test database). Run them with the virtualenv active, or prefix the commands with `uv run`.
Selenium tests (`tests/integration/`, marker `selenium`) also need Chrome/Chromium.

| Command | What it runs |
|---------|--------------|
| `make test` | `pytest tests/`: everything except Selenium tests (excluded by `pytest.ini`), reusing the test database; HTML coverage in `~build/coverage/` |
| `make test-fast` | all tests **including** Selenium, in parallel (`-n auto`), headless, without coverage |
| `make test-cov` | all tests including Selenium on a fresh database, with coverage (XML, HTML, terminal) and a JUnit report in `~build/`; opens the HTML report if `BROWSERCMD` is set |
| `tox` | the same checks as CI, in a clean environment: `lint` (all pre-commit hooks), `tests` (all tests including Selenium, in parallel, fresh database), `docs` (MkDocs build), `pkg_meta` (package build) |
| `tox -e tests` / `tox -e lint` / `tox -e docs` | a single tox environment |

Other useful invocations:

```bash
pytest tests/unit/missions/test_mission_model.py   # a single file
pytest -m selenium tests/integration               # Selenium tests only
```

Frontend tests run inside `krm3-fe/`:

```bash
yarn test                # Vitest in watch mode (npx vitest run for a single run)
npx tsc --noEmit -p .    # type check
```

## Pull requests

1. Push your branch and open a PR to develop.
2. Make sure all automated checks pass: run `tox` (see [Running tests](#running-tests)) and,
   for frontend changes, the frontend tests.
3. Ask for review from at least one maintainer.
4. Once approved, the PR can be merged. If you have merge rights, you may merge it yourself; otherwise, a maintainer will merge it.

## Releases and deployment

- **Do not bump the version or update the changelog in your PRs.** Releases and deployments are handled by the
  maintainers.
- The release process (version bump, release PR from `develop` to `master`, deployment to krm3int and
  production) is described in [RELEASE.md](./RELEASE.md).

## Code of conduct

Be respectful and constructive. For anything that needs internal context, maintainers will route you to the right place.
