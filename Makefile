BUILDDIR='.build'
PYTHONPATH:=${PWD}/tests/:${PWD}:${PYTHONPATH}
BUILDDIR?=./.build
CURRENT_BRANCH:=$(shell git rev-parse --abbrev-ref HEAD)
NODE_ENV?=production
.PHONY: help runonce run i18n
.DEFAULT_GOAL := help

ifeq ($(wildcard .python-version),)
    PYTHON_VERSION = ""
else
    PYTHON_VERSION = $(shell head -1 .python-version)
endif

ifeq ($(wildcard .initialized),)
    INITIALIZED = 0
else
    INITIALIZED = 1
endif

guard-%:
	@if [ "${${*}}" = "" ]; then \
		echo "Environment variable $* not set"; \
        exit 1; \
    fi


define BROWSER_PYSCRIPT
import os, webbrowser, sys

from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z0-9_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

BROWSER := python -c "$$BROWSER_PYSCRIPT"

help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

.mkbuilddir:
	@mkdir -p ${BUILDDIR}


backup_file := ~$(shell date +%Y-%m-%d).json
reset-migrations: ## reset django migrations
	./manage.py check
	find src -name '0*[1,2,3,4,5,6,7,8,9,0]*' | xargs rm -f
	rm -f *.db
	./manage.py makemigrations krm3
	./manage.py makemigrations --check
	@echo "\033[31;1m You almost there:"
	@echo "\033[37;1m  - add 'CITextExtension()' as first operations of src/krm3/migrations/0001_initial.py"
	@echo "\033[37;1m  - run ./manage.py upgrade --no-input"
	@echo "\033[37;1m  - run ./manage.py demo --no-input"


lint:  ## code lint
	pre-commit run --all-files

clean: ## clean development tree
	rm -fr ${BUILDDIR} build dist src/*.egg-info .coverage coverage.xml .eggs .pytest_cache *.egg-info
	find src -name __pycache__ -o -name "*.py?" -o -name "*.orig" -prune | xargs rm -rf
	find tests -name __pycache__ -o -name "*.py?" -o -name "*.orig" -prune | xargs rm -rf
	find src/_other_/locale -name django.mo | xargs rm -f

fullclean:
	rm -fr .tox .cache .venv node_modules
	$(MAKE) clean

test:
	pytest tests/

.init-db:
	sh tools/dev/initdb.sh

.zap-migrations_:
	@if [ "`find src -name "0*.py" | grep "/migrations/"`" != "" ]; then \
       rm `find src -name "0*.py" | grep "/migrations/"` ; \
    fi
#	@./manage.py makemigrations

.upgrade:
	./manage.py upgrade -vv


.zap: .init-db .upgrade .loaddata

.zap-migrations: .zap-migrations_ .zap  ## Destroys and recreate migrations


.check-python-version:
	@if [ "${PYTHON_VERSION}" = "" ]; then \
		echo "No .python-version specified in ${PRJ} . Will not create venv" ; \
		echo "ABORTING venv creation. Please ignore following error" ; \
		exit 1 ; \
	else \
	  	echo "Do you want to continue setting up a venv?  (y/N)"; \
		read ANS; \
		if [ "$${ANS}" != "y" ]; then \
			echo "DECLINE venv creation. Please ignore following error" ; \
			exit 1 ; \
		fi \
	fi

.dumpdata:
	@./manage.py dumpdata --format yaml --natural-foreign --natural-primary auth > tools/zapdata/demo/groups.yaml
	@./manage.py dumpdata --format yaml --natural-foreign --natural-primary currencies.currency > tools/zapdata/demo/currencies.yaml
	@./manage.py dumpdata --format yaml --natural-foreign --natural-primary currencies.rate > tools/zapdata/demo/rates.yaml
	@./manage.py dumpdata --format yaml --natural-foreign --natural-primary core  > tools/zapdata/demo/core.yaml
	@./manage.py dumpdata --format yaml --natural-foreign --natural-primary missions  > tools/zapdata/demo/missions.yaml
	@./manage.py dumpdata --format yaml --natural-foreign --natural-primary krm3  > tools/zapdata/demo/krm3.yaml
	@cp -R ~media/* tools/zapdata/demo/media

.loaddata:
	@-./manage.py loaddata tools/zapdata/demo/currencies.yaml
	@-./manage.py loaddata tools/zapdata/demo/rates.yaml
	@./manage.py loaddata tools/zapdata/demo/groups.yaml
	@-./manage.py loaddata tools/zapdata/demo/core.yaml
	@-./manage.py loaddata tools/zapdata/demo/missions.yaml
	@-./manage.py loaddata tools/zapdata/demo/krm3.yaml
	@cp -R tools/zapdata/demo/media/* ~media

test-fast: ## runtest integration and unit tests in parallel
	@pytest -n auto -m "selenium or not selenium" --no-cov --headless

test-cov: ## run tests with coverage
	@pytest -n auto -m "selenium or not selenium" tests --create-db --junitxml=`pwd`/~build/pytest.xml -vv \
        --cov-report=xml:`pwd`/~build/coverage.xml --cov-report=html --cov-report=term \
        --cov-config=tests/.coveragerc \
        --cov=krm3
	@if [ "${BROWSERCMD}" != "" ]; then \
    	${BROWSERCMD} `pwd`/~build/coverage/index.html ; \
    fi

run:  ## Run a Django development webserver (assumes that `runonce` was previously run).
	npm run build
	./manage.py runserver


detect-secrets:  ## Scanning secrets or adding New Secrets to Baseline
	@if [ ! -f ".secrets.baseline" ]; then \
  		echo "Initialising secrets" ; \
		detect-secrets scan > .secrets.baseline ; \
	fi
	@detect-secrets scan --baseline .secrets.baseline

schema:  # Generates the swagger file schema.yml
	@./manage.py spectacular --color --file schema.yml

schema-serve: schema  # Runs a docker container for serving the schema
	@docker run --rm -p 8080:8080 -e SWAGGER_JSON=/schema.yml -v ${PWD}/schema.yml:/schema.yml swaggerapi/swagger-ui

outdated:  ## Generates .outdated.txt and .tree.txt files
	uv tree > .tree.txt
	uv pip list --outdated > .outdated.txt

act-docs:
	act -W '.github/workflows/docs.yml' push --job generate
	cd .artifacts/1/github-pages && tar -xzvf github-pages.zip

release:
	@echo "Generating release.json with BE and FE version info"
	@BE_BRANCH=`git branch --show-current` \
	BE_COMMIT=`git rev-parse --short HEAD` \
	BE_DATE=`git log -1 --pretty=%ad --date=short` && \
	BE_VER=`python -c "import tomllib; f=open('pyproject.toml', 'rb'); data = tomllib.load(f); print(data['project']['version'])"` && \
	cd ./krm3-fe && \
	FE_VER=`npm pkg get version` \
	FE_BRANCH=`git branch --show-current` \
	FE_COMMIT=`git rev-parse --short HEAD` \
	FE_DATE=`git log -1 --pretty=%ad --date=short` && \
	cd .. && \
	printf '{\n"be": {"branch": "'$$BE_BRANCH'", "commit": "'$$BE_COMMIT'", "date": "'$$BE_DATE'", "version": "'$$BE_VER'"},\n"fe": {"branch": "'$$FE_BRANCH'", "commit": "'$$FE_COMMIT'", "date": "'$$FE_DATE'", "version": '$$FE_VER'}\n}' > src/krm3/core/static/release.json

refresh-fe:  ## rebuilds FE and tailwind
	@cd krm3-fe && git pull && yarn install && yarn build
	@git pull && uv sync && ./manage.py tailwind build

compilemessages:  # Compiles i18n skipping .tox and .venv
	@./manage.py compilemessages -i .tox -i .venv
