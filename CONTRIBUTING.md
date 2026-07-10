# Contributing to KRM3

Thank you for contributing to KRM3! This repository is public, so the instructions below are self-contained and do not require access to internal tools such as Docmost.

## Prerequisites

- [UV](https://docs.astral.sh/uv/getting-started/installation/)
- [Ruff](https://docs.astral.sh/ruff/installation/) (linting)
- [PostgreSQL](https://postgresql.org)
- (Optional) [direnv](https://direnv.net/docs/installation.html)

For detailed local setup, see [README.md](./README.md).

## Branching model

- Long-lived branches:
  - `develop`: integration branch — target all PRs here.
  - `master`: release branch — only maintainers merge release PRs here.

## Branch naming

- Feature branches: `feature/<ticket-number>-short-description` or `feat/<ticket-number>-short-description`
- Bug/hotfix branches: `bug/<ticket-number>-short-description` or `fix/<ticket-number>-short-description`

## Commits

KRM3 uses [Conventional Commits](https://www.conventionalcommits.org/) to drive the changelog and versioning:

| Type | SemVer bump |
|------|-------------|
| `fix:` | patch |
| `feat:` | minor |
| `BREAKING CHANGE:` | major |

You can use Commitizen for an interactive prompt:

```bash
cz commit
```

Squash work-in-progress commits before merging if needed.

## Pull requests

1. Push your branch and open a PR to develop.
2. Make sure all automated checks pass (tests, lint, etc.).
3. Ask for review from at least one maintainer.
4. Once approved, the PR can be merged. If you have merge rights, you may merge it yourself; otherwise, a maintainer will merge it.

## Releases and deployment

- **Do not bump the version or update the changelog yourself.** The release manager prepares the release PR from `develop` to `master`.
- Releases and deployments are handled by the maintainers.

## Code of conduct

Be respectful and constructive. For anything that needs internal context, maintainers will route you to the right place.
