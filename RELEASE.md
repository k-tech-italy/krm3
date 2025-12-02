## TL;DR

This document outlines the release process for KRM3, which involves the following key steps:

1.  **Development**: All changes are made in feature branches and merged into the `develop` branch via Pull Requests.
2.  **Automated Versioning**: When ready the `Build and Deploy` GitHub Actions workflow is manually triggered, which uses Commitizen to automatically bump the version number.
3.  **Build and Publish**: The workflow builds the frontend, creates a Docker image, and pushes it to the GitHub Container Registry.
4.  **Manual Approval**: The workflow pauses for manual approval before deploying to the development environment.
5.  **Development Deployment**: After approval, the new version is automatically deployed to the `krm3int` development Kubernetes cluster.
6.  **Production Deployment**: Production deployment is a manual process that must be coordinated with the DevOps team or the Development Team Leader.

# Release Process

This document describes the process for releasing a new version of KRM3.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Release Workflow](#release-workflow)
- [Deployment Stages](#deployment-stages)
- [Workflow Details](#workflow-details)
- [Troubleshooting](#troubleshooting)

## Overview

KRM3 follows a structured release process that ensures code quality through peer review, automated version management with Commitizen, and controlled deployments across multiple environments.

The release flow follows these stages:
1. **Development** → Feature branches merged to `develop` via Pull Requests
2. **Version Bump** → Automated version bump using Commitizen
3. **Build & Publish** → Docker image published to GitHub Container Registry
4. **Manual Approval** → Wait for manual approval in GitHub Actions
5. **Development Deployment (krm3int)** → Automated deployment to development Kubernetes cluster after approval
6. **Production Deployment** → Completely manual process (requires DevOps/Team Leader)

## Prerequisites

Before starting a release, ensure:

- [ ] All changes have been committed to a feature branch
- [ ] At least one commit follows the [Conventional Commits](https://www.conventionalcommits.org/) specification (created using `cz commit`)
- [ ] All tests are passing
- [ ] Code has been reviewed

## Release Workflow

### 1. Create a Pull Request

Create a PR from your feature branch to `develop`:

```bash
git checkout -b feature/my-feature
# Make your changes
cz commit  # Use Commitizen to create conventional commits
git push origin feature/my-feature
```

**Important**: The PR must contain at least one commit created with `cz commit` that will be used by Commitizen to determine the version bump (patch, minor, or major).

### 2. Review and Merge

- Request code review from team members
- Address any feedback
- Once approved, merge the PR into `develop`

### 3. Trigger Release Workflow

After the PR is merged into `develop`, manually trigger the deployment workflow:

1. Go to the [Actions tab](https://github.com/k-tech-italy/krm3/actions) in GitHub
2. Select the **Build and Deploy** workflow
3. Click **Run workflow**
4. Select the `develop` branch
5. Click **Run workflow**

This will initiate the automated release process.

## Deployment Stages

### Stage 1: Version Bump (Automated)

The workflow automatically:
- Runs `cz bump --yes` to analyze commits and determine the new version
- Updates version in:
  - [pyproject.toml](pyproject.toml#L3)
  - [src/krm3/__init__.py](src/krm3/__init__.py)
  - [docker/Makefile](docker/Makefile)
  - [src/krm3/config/fragments/serviceworker.js](src/krm3/config/fragments/serviceworker.js)
- Updates [CHANGELOG.md](CHANGELOG.md) with changes since version 1.5.32
- Creates a git tag with the new version
- Pushes the bump commit and tags to `develop`
- Merges `develop` into `master` (temporarely disabled)
- Pushes `master` (temporarely disabled)

### Stage 2: Frontend Build (Automated)

The workflow:
- Checks out the code at the new version commit
- Sets up Python 3.12.1 and uv package manager
- Installs dependencies using `uv sync`
- Initializes the frontend submodule (`krm3-fe`)
- Builds the frontend using Yarn
- Generates `release.json` with version information
- Uploads the built frontend as an artifact

### Stage 3: Docker Build & Push (Automated)

The workflow:
- Downloads the built frontend artifact
- Builds the Docker image using [docker/Dockerfile](docker/Dockerfile)
- Tags the image with:
  - Version tag: `ghcr.io/k-tech-italy/krm3:<version>`
  - Latest tag: `ghcr.io/k-tech-italy/krm3:latest`
- Pushes to [GitHub Container Registry](https://github.com/k-tech-italy/krm3/pkgs/container/krm3)

### Stage 4: Manual Approval (Manual)

After the Docker image is successfully built and pushed:

1. The workflow pauses and waits for **manual approval** in the GitHub Actions "development" environment
2. A team member with appropriate permissions must review and approve the deployment
3. Go to the [Actions tab](https://github.com/k-tech-italy/krm3/actions) and approve the pending deployment

### Stage 5: Development Environment Deployment (krm3int) - Automated

After manual approval, the workflow automatically:
- Calls the Rancher API to deploy the application to the **krm3int development Kubernetes cluster**
- Uses environment variables:
  - `RANCHER_URL`: Rancher API endpoint
  - `RANCHER_TOKEN`: Authentication token
- Verifies deployment success (HTTP 200 response)

**Important**: This deployment is **only to the krm3int development environment**. This is the final step of the automated pipeline.

### Stage 6: Production Deployment (Completely Manual)

**The automated workflow does NOT deploy to production.** Production deployment is a completely separate manual process:

1. After verifying the deployment works correctly in krm3int development environment
2. Contact a member of the **DevOps team** or the **Development Team Leader**
3. Provide them with:
   - The new version number
   - Confirmation that krm3int testing is complete
4. The DevOps team or Team Leader will manually perform the production deployment using their own tools and procedures

**Note**: There is no automated production deployment in this pipeline.

## Workflow Details

### Workflow File

The complete workflow is defined in [.github/workflows/deploy.yml](.github/workflows/deploy.yml).

### Jobs Overview

1. **`bump`**: Version bumping and git operations
2. **`build-frontend`**: Frontend compilation and artifact creation
3. **`build-and-push`**: Docker image creation and registry push
4. **`release`**: Manual approval gate + deployment to krm3int development environment via Rancher API

### Commitizen Configuration

Commitizen is configured in [pyproject.toml](pyproject.toml#L154-L165):

```toml
[tool.commitizen]
name = "cz_conventional_commits"
tag_format = "$version"
version_scheme = "pep440"
version_provider = "uv"
update_changelog_on_bump = true
changelog_start_rev = "1.5.32"
version_files = [
    "src/krm3/__init__.py:__version__",
    "docker/Makefile:VERSION",
    "src/krm3/config/fragments/serviceworker.js:_version",
]
```

### Version Determination

Commitizen determines the version bump based on commit messages:

- `fix:` → Patch version (e.g., 2.2.1 → 2.2.2)
- `feat:` → Minor version (e.g., 2.2.1 → 2.3.0)
- `BREAKING CHANGE:` or `!` → Major version (e.g., 2.2.1 → 3.0.0)

## Troubleshooting

### Build Failures

If the workflow fails during build:
1. Check the GitHub Actions logs for specific errors
2. Ensure all dependencies are correctly specified in [pyproject.toml](pyproject.toml)
3. Verify the frontend submodule is properly configured

### Version Bump Failures

If version bump fails:
1. Ensure at least one commit uses the Conventional Commits format
2. Check that the version in [pyproject.toml](pyproject.toml#L3) is valid
3. Verify Commitizen can access the git history (`fetch-depth: 0`)

### Deployment Failures

If deployment to krm3int development environment fails:
1. Verify the Rancher API credentials are correctly configured in GitHub Secrets (`RANCHER_URL` and `RANCHER_TOKEN`)
2. Check that the krm3int Kubernetes cluster is accessible
3. Review Rancher logs for deployment issues
4. Verify the Docker image was successfully pushed to the registry
5. Check the Rancher API response for specific error messages

### Docker Registry Push Failures

If image push fails:
1. Verify GitHub Actions has `packages: write` permission
2. Check that the GitHub Container Registry is accessible
3. Ensure the image name follows the correct format

## Additional Resources

- [Conventional Commits Specification](https://www.conventionalcommits.org/)
- [Commitizen Documentation](https://commitizen-tools.github.io/commitizen/)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [GitHub Actions Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)

## Contact

For questions or issues with the release process:
- **DevOps Team**: Contact for production deployment assistance
- **Team Leader**: For release approval and coordination
- **Development Team**: For build and integration issues
