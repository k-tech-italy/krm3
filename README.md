# Development environment setup

1. Prerequisites

   1. direnv and pyenv installed in your system. **Ensure shell hooks are installed before proceeding!**
   1. Install python binaries with pyenv (see [Install python binaries and poetry](#Install python binaries and poetry) in _Details_ section)
   1. Create an empty postgres database (eg. "krm3")
   1. Copy .env.example and .envrc.example in equivalent .env and .envrc (which are NOT versioned as they may contain secrets)
   1. Amend local .env (and .envrc as needed). Most importantly set the KRM3_DATABASE_URL pointing to you database
   1. Run _direnv allow_ (needed each time you modify .envrc or you want to reload the .env)
   1. cd && cd - && poetry install

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
