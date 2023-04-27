# Development environment setup

1. Prerequisites

   1. direnv and pyenv installed in your system. **Ensure shell hooks are installed before proceeding!** _Alternatives are possible, see below._
   1. Install python binaries with pyenv (see [Install python binaries and poetry](#Install python binaries and poetry) in _Details_ section).
   1. Create an empty postgres database (eg. "krm3").
   1. Copy .env.example and .envrc.example in equivalent .env and .envrc (which are NOT versioned as they may contain secrets).
   1. Amend local .env (and .envrc as needed). Most importantly set the KRM3_DATABASE_URL pointing to you database.
   1. Run `direnv allow` (needed each time you modify .envrc or you want to reload the .env).
   1. `cd && cd - && poetry install`

Now you should have a fully working environment

# Details

## Install python binaries and poetry

Installation in one line:
```shell
export NEEDED_VER=`head -1 .python-version`
mkdir /tmp/t ; cd /tmp/t ; pyenv install $NEEDED_VER ; pyenv local 3.11.0; pip install -U pip poetry
```

Explanation:
We user a temporary folder from where to:
1. install needed python version (whatever version needed from .python-version)
1. point to the newly installed binaries
1. Upgrade _pip_ to latest version and install latest version of _poetry_
1. ONLY ONCE per system (not per binaries) set poetry to create virtualenvens in a local _.venv_ folder: `poetry config virtualenvs.in-project true`


Example setup from scratch:
```shell
~/PROJS/KT>git clone https://git.k-tech.it/kt-internal/krm3.git
Cloning into 'krm3'...
remote: Enumerating objects: 169, done.
remote: Counting objects: 100% (169/169), done.
remote: Compressing objects: 100% (131/131), done.
remote: Total 269 (delta 54), reused 82 (delta 18), pack-reused 100
Receiving objects: 100% (269/269), 169.66 KiB | 1.84 MiB/s, done.
Resolving deltas: 100% (72/72), done.
~/PROJS/KT>cd krm3
~/PROJS/KT/krm3(develop)>cp .env.example .env
~/PROJS/KT/krm3(develop)>cp .envrc.example .envrc
direnv: error /Users/gigio/PROJS/KT/krm3/.envrc is blocked. Run `direnv allow` to approve its content
~/PROJS/KT/krm3(develop)>direnv allow
direnv: loading ~/PROJS/KT/krm3/.envrc
direnv: No created poetry virtual environment found. Use `poetry install` to create one first.
~/PROJS/KT/krm3(develop)>pyenv local
3.11.0
~/PROJS/KT/krm3(develop)>python --version
Python 3.11.0
~/PROJS/KT/krm3(develop)>which python
/Users/gigio/.pyenv/shims/python
~/PROJS/KT/krm3(develop)>which poetry
/Users/gigio/.pyenv/shims/poetry
~/PROJS/KT/krm3(develop)>poetry install
Configuration file exists at /Users/gigio/Library/Application Support/pypoetry, reusing this directory.

Consider moving configuration to /Users/gigio/Library/Preferences/pypoetry, as support for the legacy directory will be removed in an upcoming release.
Installing dependencies from lock file

Package operations: 83 installs, 1 update, 0 removals

  • Installing markupsafe (2.1.2): Pending...
  • Installing pytz (2022.7.1): Pending...
  • Installing requests (2.28.2): Pending.
  ... ... ...
    • Installing uwsgi (2.0.21)

Installing the current project: krm3 (0.1.0)

~/PROJS/KT/krm3(develop)>curl -X POST http://127.0.0.1:8000/auth/users/ --data 'email=djoser@k-tech.it&first_name=gio&last_name=bronz&password=alpine12'
{"first_name":"gio","last_name":"bronz","email":"djoser@k-tech.it","id":2}

```


# Alternatives
Some alternatives for project setup.

## Without pyenv
You can use virtual env manually:

```mkvirtualenv -p `which python3.11`  krm3```

`workon krm3`

Pay attention: Poetry will create a sub-virtualenv to avoid this check its configuration and set a couple of settings:
````
poetry config --list
poetry config virtualenvs.create false
poetry config virtualenvs.prefer-active-python true
````

## Without direnv
You have to manually export all vars in .env before running `./manage.py` use the following command on linux and macos:

`set -o allexport; source .env; set +o allexport`

Tip: `npm start` is configured to do exactly this + `./manage.py runserver`. Easy peasy.

## Without psql
Manually create a database `krm3` and inside it a schema named `django`. This can be done with pgadmin or similar tools.
Then do what `make .zap` would do skipping init-db.
```
./manage.py upgrade -vv
./manage.py demo setup
```
