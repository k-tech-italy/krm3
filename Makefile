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


static:  ## build static assets
	@rm -fr src/krm3/web/static/*
	@sass src/krm3/web/assets/tw.in.scss | postcss  --config   -o src/krm3/web/assets/tw.css
	@node_modules/.bin/webpack --mode ${NODE_ENV} --progress  --bail
	@STATIC_ROOT=src/krm3/web/static ./manage.py collectstatic_js_reverse -v 0
	@STATIC_ROOT=src/krm3/web/static ./manage.py collectstatic --no-input -v 0
	@git add src/krm3/web/static
	@echo $(shell /bin/ls -alu src/krm3/web/static/krm3/app.js)
	@echo $(shell /bin/ls -alu src/krm3/web/static/krm3/app.css)


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

bump:   ## Bumps version
	@while :; do \
		read -r -p "bumpversion [major/minor/patch]: " PART; \
		case "$$PART" in \
			major|minor|patch) break ;; \
  		esac \
	done ; \
	bumpversion --no-commit --allow-dirty $$PART
	@grep "^version = " pyproject.toml

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


test-cov: ## run tests with coverage
	@pytest tests --create-db --junitxml=`pwd`/~build/pytest.xml -vv \
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
