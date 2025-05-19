# TL;DR;

## Mandatory requirements

- [UV](https://docs.astral.sh/uv/getting-started/installation/) as package manager, venv manager, and for managing Python binaries
- [Ruff](https://docs.astral.sh/ruff/installation/) as code linter/verifier
- [PostgreSQL](https://postgresql.org) as the database.

## Optional requirements

- [direnv](https://direnv.net/docs/installation.html) for automating local environment configuration loading/unloading

## Preparation

* Clone the repo.

    ```shell
    git clone https://github.com/k-tech-italy/krm3.git
    cd krm3

    # switch to your working branch - use the `-c` flag to create a new one
    git switch <your working branch>
    ```

* Prepare the Python environment for the project.

    ```shell
    # Install Python binaries
    # see https://github.com/k-tech-italy/krm3/blob/uv/.python-version for the version to install
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

* If using `direnv`:
    ```shell
    cp .envrc.example .envrc
    direnv allow
    ```
  Whenever you make a change to your `.env` or `.envrc` files, you need to run `direnv reload` or `direnv allow` to apply them.

- Install pre-commit-hooks
  ```bash
  # Install pre-commit checks
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
  ./manage.py tailwind start
  ```

... and then the runserver in another terminal

  ```bash
  ./manage.py runserver localhost:8000
  ```

Hint: See
- src/krm3/web/templates/example.html as an example page with some cotton components
- src/krm3/templates/cotton/card.html for the cotton card component
- src/krm3/theme/static_src/src/styles.scss for the master theme styles.css
(NB: `@source "../../../**/*.{html,js}"` to capture styles from Django apps)
