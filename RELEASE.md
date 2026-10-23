# Release process

How a new KRM3 version is released and deployed. This is the only description of the process: CONTRIBUTING.md,
AGENTS.md and the developer guide refer to this file. Releases are done by the maintainers.

## TL;DR

1. **Development**: changes reach `develop` through Pull Requests, with Conventional Commits.
2. **Version bump** on `develop` (required: the pipeline refuses a version that is already published):
    - point the `krm3-fe` submodule at the frontend commit to release (the pipeline builds it);
    - run `cz bump`: it commits the new version and changelog and creates the tag;
    - push `develop` and the new tag.
3. **Release PR**: open a PR from `develop` to `master`, describe the release in it and merge it with a
   merge commit (not *Rebase and merge*).
4. **Build and Deploy** (automatic, on the push to `master`): the Docker image is published to the GitHub
   Container Registry and deployed to the `krm3int` development cluster. There is no approval step.
5. **Production**: run the **Deploy to Production** GitHub action by hand with the new version.

## Contents

- [Before you start](#before-you-start)
- [1. Bump the version](#1-bump-the-version)
- [2. Open and merge the release PR](#2-open-and-merge-the-release-pr)
- [3. Build and Deploy (automatic)](#3-build-and-deploy-automatic)
- [4. Deploy to production](#4-deploy-to-production)
- [Commitizen](#commitizen)
- [Troubleshooting](#troubleshooting)

## Before you start

- Everything to release is merged into `develop` through reviewed Pull Requests (see CONTRIBUTING.md), and
  the tests on `develop` pass.
- Since the last release there is at least one commit whose type changes the version (`fix`, `feat` or a
  breaking change, see [Commitizen](#commitizen)); otherwise `cz bump` has nothing to bump.
- Note anything the deployment needs beyond the new image, such as manual database work: it goes in the
  release PR description.

## 1. Bump the version

On an up-to-date `develop`:

```bash
git switch develop && git pull
# if the frontend changed: point krm3-fe at the commit to release and commit the pointer
cz bump --dry-run          # optional: shows the new version and the changelog entry
cz bump
git push origin develop
git push origin <new version>    # e.g. git push origin 4.1.0
```

`cz bump` reads the commits since the last tag, picks the new version and:

- updates the version in
  [pyproject.toml](https://github.com/k-tech-italy/krm3/blob/develop/pyproject.toml) (and `uv.lock`),
  [src/krm3/\_\_init\_\_.py](https://github.com/k-tech-italy/krm3/blob/develop/src/krm3/__init__.py),
  [docker/Makefile](https://github.com/k-tech-italy/krm3/blob/develop/docker/Makefile) and
  [serviceworker.js](https://github.com/k-tech-italy/krm3/blob/develop/src/krm3/config/fragments/serviceworker.js);
- adds the new version to [CHANGELOG.md](https://github.com/k-tech-italy/krm3/blob/develop/CHANGELOG.md);
- commits these changes as `bump: version X -> Y` and creates the annotated tag `Y` (no `v` prefix).

The tag is only local until you push it. The frontend is built by the pipeline from the commit the `krm3-fe`
submodule points to, so updating that pointer is all the frontend needs.

This step is required: when `master` receives a version that is already in the registry, the **Build and
Deploy** workflow stops with `Version X already exists in the container registry!` and nothing is deployed.

## 2. Open and merge the release PR

Open a Pull Request from `develop` to `master`. Its description is the release note:

- the changes, grouped as features, fixes, documentation and others;
- anything that has to be done by hand around the deployment (e.g. database steps), at the top.

Merge it with **Create a merge commit** (`gh pr merge <number> --merge`), not *Rebase and merge*. The merge
commit keeps the `develop` commits, and the release tag on the bump commit, in the history of `master`, so the
next release PR contains only the new commits.

Rebasing would copy the commits onto `master` with new hashes. `develop` would then no longer be part of the
history of `master`, and the next release PR would have to replay every earlier commit again: GitHub refuses it
with `This branch can't be rebased` once those copies conflict.

## 3. Build and Deploy (automatic)

The push to `master` runs the **Build and Deploy** workflow
([.github/workflows/deploy.yml](https://github.com/k-tech-italy/krm3/blob/develop/.github/workflows/deploy.yml)).
Its jobs:

1. **`validate`**: reads the version from `pyproject.toml` and checks it against the images in the registry:
   it must not exist yet and must be higher than the highest published version.
2. **`build-frontend`**: installs the dependencies, initialises the `krm3-fe` submodule, builds the frontend
   with Yarn, generates `release.json` (`make release`) and uploads the result as an artifact.
3. **`build-and-push`**: builds the Python package and the Docker image
   ([docker/Dockerfile](https://github.com/k-tech-italy/krm3/blob/develop/docker/Dockerfile)) and pushes it as
   `ghcr.io/k-tech-italy/krm3:<version>` and `ghcr.io/k-tech-italy/krm3:latest` to the
   [GitHub Container Registry](https://github.com/k-tech-italy/krm3/pkgs/container/krm3).
4. **`release`**: calls the Rancher API (`RANCHER_URL`, `RANCHER_TOKEN`) to redeploy the **krm3int** development
   environment, and fails unless Rancher answers HTTP 200.

There is no approval step: the `release` job does not use the protected `development` environment. The workflow
never deploys to production.

## 4. Deploy to production

After checking the new version on krm3int, run the **Deploy to Production** workflow
([.github/workflows/prod-deploy.yml](https://github.com/k-tech-italy/krm3/blob/develop/.github/workflows/prod-deploy.yml)):

1. go to the [Actions tab](https://github.com/k-tech-italy/krm3/actions) and select **Deploy to Production**;
2. click **Run workflow** and enter the backend version to deploy (e.g. `4.1.0`).

The workflow reads `https://krm3int.k-tech.it/static/release.json` and aborts if the requested version is higher
than the one running on krm3int; it then points the production deployment at
`ghcr.io/k-tech-italy/krm3:<version>` through the Rancher API. The same workflow rolls production back to an
earlier version.

## Commitizen

Commitizen is configured in
[pyproject.toml](https://github.com/k-tech-italy/krm3/blob/develop/pyproject.toml) under `[tool.commitizen]`:

```toml
[tool.commitizen]
name = "cz_conventional_commits"
tag_format = "$version"
version_scheme = "pep440"
version_provider = "uv"
annotated_tag = true
update_changelog_on_bump = true
changelog_start_rev = "1.5.32"
version_files = [
    "src/krm3/__init__.py:__version__",
    "docker/Makefile:VERSION",
    "src/krm3/config/fragments/serviceworker.js:_version",
]
```

The new version depends on the commit types since the last tag (see CONTRIBUTING.md for all the types):

| Commits | Bump | Example |
|---|---|---|
| `fix:` | patch | 2.2.1 -> 2.2.2 |
| `feat:` | minor | 2.2.1 -> 2.3.0 |
| `BREAKING CHANGE:` footer or `!` after the type | major | 2.2.1 -> 3.0.0 |

Commit with `cz commit` to get the format right; the `commit-msg` hook rejects messages that do not follow it.

## Troubleshooting

### `Version X already exists in the container registry!`

The release reached `master` without a version bump. Bump the version on `develop`
(see [1. Bump the version](#1-bump-the-version)) and open a new release PR: the push to `master` runs the
workflow again.

### `This branch can't be rebased` on the release PR

The release PR was set to *Rebase and merge* while `master` already holds rebased copies of some `develop`
commits. Merge it with a merge commit instead (see
[2. Open and merge the release PR](#2-open-and-merge-the-release-pr)).

### `cz bump` finds nothing to bump

No commit since the last tag has a type that changes the version (only `docs`, `test`, `chore`, ...), or the
commit messages do not follow Conventional Commits. Commitizen also needs the tags of earlier releases: check
that the last release tag is in your clone (`git describe --tags --abbrev=0`).

### Build failures

1. Check the GitHub Actions logs for the failing job.
2. Make sure the dependencies are correct in `pyproject.toml` and `uv.lock` (the workflow runs
   `uv sync --frozen`).
3. Check that the `krm3-fe` submodule points at a commit that exists in the frontend repository and builds.

### Docker registry push failures

1. Check that the workflow has the `packages: write` permission.
2. Check that the GitHub Container Registry is reachable.

### Deployment failures (krm3int or production)

1. Check the Rancher credentials: the `RANCHER_URL` variable and the `RANCHER_TOKEN` secret.
2. Check that the Kubernetes cluster is reachable and look at the Rancher logs and the API response.
3. Check that the image `ghcr.io/k-tech-italy/krm3:<version>` exists in the registry.

## Additional resources

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Commitizen documentation](https://commitizen-tools.github.io/commitizen/)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)

## Contact

- **DevOps team**: production deployments
- **Team leader**: release approval and coordination
- **Development team**: build and integration issues
