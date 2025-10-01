#!make

.PHONY: clean

ifndef DOCKER_REGISTRY
$(error DOCKER_REGISTRY is not set)
endif

# VARIABLES
VERSION=1.6.0
BASE?=$(shell echo "${VERSION}" | sed "s/\([0-9]*\)\.\([0-9]*\)\.\(.*\)/\1.\2/g" )
BUILDDIR?=./~build
CONTAINER_NAME=kt-krm3
IMAGE_PREFIX=k-tech-italy
DOCKER_IMAGE=${IMAGE_PREFIX}/krm3
DOCKER_IMAGE_NAME=${DOCKER_IMAGE}:${VERSION}
DOCKER_IMAGE_FULLNAME=${DOCKER_REGISTRY}/${DOCKER_IMAGE}:${VERSION}
STACK_PROTOCOL?=https
SEC_TEST_FOLDER?=$(PWD)/../~sec_test

LOCAL_PORT?=18000
LOCAL_HTTPS_PORT?=18443

CMD?=run
BUILD_OPTIONS?=--squash

# HELP HELPER
define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT


help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

requirements:  ## Builds the /dist/image-requirements.txt
	@cd .. && uv build --sdist
	@uv export --no-dev --no-emit-project --group image --format requirements-txt > ../dist/image-requirements.txt
	@uv export --no-emit-project --group dev --format requirements-txt --prune opencv-python > ../dist/test-requirements.txt

compile:
	@cd ../krm3-fe && yarn install && yarn build
	@cd .. && ./manage.py tailwind build

build: compile requirements ## Builds the image
	cd .. && docker build \
		${BUILD_OPTIONS} \
		--platform linux/amd64 \
		--progress plain \
		--target final \
		--build-arg VERSION="${VERSION}" \
		--build-arg DOCKER_REGISTRY="${DOCKER_REGISTRY}" \
		-t ${DOCKER_IMAGE_FULLNAME} \
		-f docker/Dockerfile .
	@docker images | grep ${DOCKER_IMAGE} | grep ${VERSION}

build-test: compile  requirements ## Builds the test image with dev dependencies
	cd .. && docker build \
		${BUILD_OPTIONS} \
		--platform linux/amd64 \
		--progress plain \
		--target test \
		--build-arg VERSION="${VERSION}" \
		--build-arg BASE_IMAGE="${BASE}" \
		--build-arg DOCKER_REGISTRY="${DOCKER_REGISTRY}" \
		-t ${DOCKER_IMAGE_FULLNAME}-test \
		-f docker/Dockerfile .
	@docker images | grep ${DOCKER_IMAGE} | grep test

registrylogin:  ## Log in to docker
	@echo "${DOCKER_PWD}" | docker login ${DOCKER_REGISTRY} -u ${DOCKER_USR} --password-stdin

save:
	@mkdir -p ../dist
	@echo "Saving image ../dist/image-${CONTAINER_NAME}-${VERSION}.tgz"
	@docker save ${DOCKER_IMAGE_FULLNAME} | gzip > ../dist/image-${CONTAINER_NAME}-${VERSION}.tgz

release:  registrylogin  ## For now manual release until we fix nexus
#	@scp -o ProxyJump=kjump ../dist/image-${CONTAINER_NAME}-${VERSION}.tgz khetz:/tmp
#	@echo "Now you can run on  the server:"
#	@echo "  docker load -i /tmp/image-${CONTAINER_NAME}-${VERSION}.tgz && rm /tmp/image-${CONTAINER_NAME}-${VERSION}.tgz"
	@docker push ${DOCKER_IMAGE_FULLNAME}
	@docker tag ${DOCKER_IMAGE_FULLNAME} ${DOCKER_REGISTRY}/${DOCKER_IMAGE}:latest
	@docker push ${DOCKER_REGISTRY}/${DOCKER_IMAGE}:latest



#release: registrylogin  ## Release the image
#	# docker push ${DOCKER_REGISTRY}/${DOCKER_IMAGE}/base:${BASE}
#	docker push ${DOCKER_IMAGE_FULLNAME}
#	docker images | grep ${DOCKER_IMAGE}
#
#nexus-release:
#	docker tag ${DOCKER_IMAGE_FULLNAME} docker.singlewave.co.uk/${DOCKER_IMAGE}:${VERSION}
#	docker push docker.singlewave.co.uk/${DOCKER_IMAGE}:${VERSION}

release-all: release nexus-release

full-release:  build-base build save release  ## buils all and releases
	@echo "Done"

.certs:
	@if [ ! -f "certs/server.crt" ]; then \
		echo "It appears that the certificates are not present."; \
		echo "Please run 'sudo ./gen-certs.sh $$USER' to soft link them from "; \
		echo "/etc/ssl/certs/`hostname`[.crt|.key]"; \
		echo ""; \
		echo "NB:"; \
		echo "1. it will prompt you to generate them first if they do not exists."; \
		echo "2. You will be able to reuse with multiple projects this pattern."; \
	fi


.run: .certs
	@docker run \
            --platform linux/amd64 \
			--rm \
	 		--name=${CONTAINER_NAME} \
			--network host \
			-p ${LOCAL_PORT}:8000 \
			-p ${LOCAL_HTTPS_PORT}:8443 \
			--env-file ../.env \
			-v "`pwd`/certs:/etc/certs:ro" \
			-v "/etc/ssl/certs:/etc/ssl/certs:ro" \
			${RUN_OPTIONS} \
			${DOCKER_IMAGE_FULLNAME} \
			${CMD}

.run-test: .certs
	@docker run \
            --platform linux/amd64 \
			--rm \
	 		--name=${CONTAINER_NAME} \
			--network host \
			-p ${LOCAL_PORT}:8000 \
			-p ${LOCAL_HTTPS_PORT}:8443 \
			--env-file ../.env \
			-v "`pwd`/certs:/etc/certs:ro" \
			-v "/etc/ssl/certs:/etc/ssl/certs:ro" \
			-v "`pwd`/../tests:/code/tests:ro" \
			-v "`pwd`/../src:/code/src:ro" \
			${RUN_OPTIONS} \
			${DOCKER_IMAGE_FULLNAME}-test \
			${CMD}

run: ## run docker container locally with http
	STACK_PROTOCOL=http $(MAKE) .run

exec: ## Connects o the running container
	@docker exec -it ${CONTAINER_NAME} /bin/bash

run-stack: ## run docker container locally with all services and https
	CMD=stack $(MAKE) .run

shell: ## run shell container
	@RUN_OPTIONS=-it CMD='/bin/bash' $(MAKE) .run

test: ## run 'django-admin check --deploy' into container
	RUN_OPTIONS=-it CMD='django-admin check --deploy' $(MAKE) .run
	RUN_OPTIONS=-it CMD='uwsgi' $(MAKE) .run

test-coverage: ## Run tests with coverage report
	@RUN_OPTIONS=-it CMD='pytest --create-db --cov=krm3 --cov-report=html --cov-report=term --ignore=tests/integration/test_gui_auth.py' $(MAKE) .run-test

stack:  ## run containder with both web/celery services
	RUN_OPTIONS=-it CMD='stack' $(MAKE) .run

security-test:
	@if [ ! $(shell which trivy) ]; then \
  		echo "Trivy not found please install it: \n curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin <version>"; \
	else \
		mkdir -p $(SEC_TEST_FOLDER); \
		trivy image --ignorefile $(PWD)/../.trivyignore ${DOCKER_IMAGE_FULLNAME} > $(SEC_TEST_FOLDER)/${CONTAINER_NAME}:${VERSION}.txt; \
		trivy image --severity HIGH,CRITICAL --ignorefile $(PWD)/../.trivyignore ${DOCKER_IMAGE_FULLNAME} > $(SEC_TEST_FOLDER)/${CONTAINER_NAME}:${VERSION}_critical_high.txt; \
	fi
