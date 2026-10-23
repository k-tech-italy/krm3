# KRM3

KRM3 is K-Tech's resource management platform: timesheets, missions and expense
reimbursements, contracts, projects, documents, currencies and contacts. The backend is a
Django application (Python, PostgreSQL); the frontend is a React single-page application kept in
the `krm3-fe` git submodule.

This file explains how to set up a local development environment. To contribute (branching,
commits, running the checks, pull requests) see [CONTRIBUTING.md](https://github.com/k-tech-italy/krm3/blob/develop/CONTRIBUTING.md).

<!--docs-setup-start-->
## TL;DR;

```shell
git clone https://github.com/k-tech-italy/krm3.git && cd krm3
git submodule init && git submodule update
(cd krm3-fe && yarn install && yarn build)
uv sync                       # Python version from .python-version
cp .env.example .env          # then set KRM3_DATABASE_URL and KRM3_LOCAL_DEVELOPMENT=True
uv run pre-commit install            # installs the pre-commit, commit-msg and pre-push hooks
uv run ./manage.py migrate && uv run ./manage.py createsuperuser
uv run ./manage.py tailwind install  # first time only; keep `./manage.py tailwind start` running
uv run ./manage.py runserver localhost:8000
```

(`uv run` is not needed when the virtualenv is active, e.g. with direnv.)

Run the tests with `make test`; see [Running tests](https://github.com/k-tech-italy/krm3/blob/develop/CONTRIBUTING.md#running-tests).

## Mandatory requirements

- [UV](https://docs.astral.sh/uv/getting-started/installation/) as package manager, venv manager, and for managing Python binaries
- [Ruff](https://docs.astral.sh/ruff/installation/) as code linter/verifier
- [PostgreSQL](https://postgresql.org) as the database
- [Node.js](https://nodejs.org/) and [Yarn](https://yarnpkg.com/) to build the frontend and the Tailwind theme
- [Commitizen](https://commitizen-tools.github.io/commitizen/) for Conventional Commits
  (`uv tool install commitizen`), see [Commits](https://github.com/k-tech-italy/krm3/blob/develop/CONTRIBUTING.md#commits)

## Optional requirements

- [direnv](https://direnv.net/docs/installation.html) for automating local environment configuration loading/unloading

## Preparation

* Clone the repo.

    ```shell
    git clone https://github.com/k-tech-italy/krm3.git
    cd krm3
    ```

  To work on a change, create a branch as described in [Branching](https://github.com/k-tech-italy/krm3/blob/develop/CONTRIBUTING.md#branching).

* Initialise the frontend

    ```shell
    git submodule init
    git submodule update

    # go into the FE folder and install dependencies and build
    cd krm3-fe
    git switch <your working FE branch>
    yarn install
    yarn build
    ```

* Prepare the Python environment for the project.

    ```shell
    # Install Python binaries
    # see .python-version for the version to install
    uv python install 3.12

    # Create the virtualenv
    uv venv

    # Install dependencies
    # Always do this every time a new dependency is added in a commit
    uv sync
    ```

* Create a dedicated database on your PostgreSQL instance (e.g. `krm3`)

* Make a copy of the dotenv example file. Make sure it is called `.env`.

    ```shell
    cp .env.example .env
    ```

* **IMPORTANT**: Edit the .env file according to your personal setup.
  * Most importantly, edit the `KRM3_DATABASE_URL` variable to match your database's DSN.
  * Set `KRM3_LOCAL_DEVELOPMENT=True`: `.env.example` has `False`, the production value. With no nginx in front of
    `runserver`, it makes Django do what nginx does in production:
    * serve the static and media files;
    * serve the frontend at `/` (without it `http://localhost:8000/` answers 404);
    * send the private files behind `/media-auth/` (expense images, contract and DMS documents) itself, instead
      of delegating them to nginx (without it they download as empty files).

* If using `direnv`:
    ```shell
    cp .envrc.example .envrc
    direnv allow
    ```
  Whenever you make a change to your `.env` or `.envrc` files, you need to run `direnv reload` or `direnv allow` to apply them.

- Install the git hooks. This installs the `pre-commit`, `commit-msg` and `pre-push` hooks
  configured in `.pre-commit-config.yaml` (see [Git hooks](https://github.com/k-tech-italy/krm3/blob/develop/CONTRIBUTING.md#git-hooks) for
  what they check).
  ```bash
  pre-commit install
  ```

- Now create your database according to your _.env_ entry *KRM3_DATABASE_URL*, apply migrations and create a superuser with:
  ```bash
  ./manage.py migrate
  ./manage.py createsuperuser
  ```

- As we are using [django-tailwind](https://django-tailwind.readthedocs.io/en/latest/) you will need to run in one
terminal the watcher process for building the theme ...

  ```bash
  ./manage.py tailwind install  # only the first time
  ./manage.py tailwind start
  ```

... and then the runserver in another terminal

  ```bash
  ./manage.py runserver localhost:8000
  ```

Hint: See
- src/krm3/theme/static_src/src/styles.scss for the master theme styles.css
(NB: `@source "../../../**/*.{html,js}"` to capture styles from Django apps)

## Keeping the frontend up to date

To bring the frontend and the backend environment up to date in one go, run:

```bash
make refresh-fe
```

It runs `git pull`, `yarn install` and `yarn build` in `krm3-fe/`, then `git pull`, `uv sync` and
`./manage.py tailwind build` in this repository. Because it pulls both repositories, commit or
stash your local changes first.
