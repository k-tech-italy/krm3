# TL;DR;

## Mandatory requirements

- [UV](https://docs.astral.sh/uv/getting-started/installation/) as package manager, venv manager, and for managing Python binaries
- [Ruff](https://docs.astral.sh/ruff/installation/) as code linter/verifier
- [Services](/Development/Development-environment/Services): a MSSQL database for testing, an S3 bucket for storing raw data server)

## Optional requirements

- [direnv](https://direnv.net/docs/installation.html) for automating local environment configuration loading/unloading

## Preparation

### Initial one-off
```shell
git clone https://dev.azure.com/worldfoodprogramme/mVAM/_git/mvam-pipelines-v2
cd mvam-pipelines-v2
git co <your working branch>  # if you need to change to a non-default branch
```

```shell
# Install Python binaries
uv python install 3.11  # or any other version required, see https://dev.azure.com/worldfoodprogramme/mVAM/_git/mvam-pipelines-v2?path=/.python-version

# Create virtualenv
uv venv

# Install dependencies
uv sync   # To be repeated whenever you pull a release requiring new dependencies

# Install pre-commit checks
pre-commit install

cp .env.example .env
```

**IMPORTANT: Now edit the content of your .env according to your needs**

If using direnv:
```shell
cp .envrc.example .envrc
direnv allow  # To be repeated whenever you change your .env or .envrc content
```
