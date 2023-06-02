#!make

.PHONY: clean

ifndef DOCKER_REGISTRY
$(error DOCKER_REGISTRY is not set)
endif

# VARIABLES
VERSION=0.3.1
BASE?=$(shell echo "${VERSION}" | sed "s/\([0-9]*\)\.\([0-9]*\)\.\(.*\)/\1.\2/g" )
BUILDDIR?=./~build
CONTAINER_NAME=kt-krm3
DOCKER_IMAGE=kt/krm3
DOCKER_IMAGE_NAME=${DOCKER_IMAGE}:${VERSION}
DOCKER_IMAGE_FULLNAME=${DOCKER_REGISTRY}/${DOCKER_IMAGE}:${VERSION}
STACK_PROTOCOL?=https

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

build-base:  ## Builds the base image
	@#poetry build --format sdist
	@poetry export --without dev --without test --with image -f requirements.txt > ../dist/image-requirements.txt
	@cd .. && docker build \
			${BUILD_OPTIONS} \
			--platform linux/amd64 \
			--build-arg REPO_NAME="${REPO_NAME}" \
			-t ${DOCKER_REGISTRY}/${DOCKER_IMAGE}/base:${BASE} \
			-f docker/Dockerfile.base  .
	#docker push ${DOCKER_REGISTRY}/${DOCKER_IMAGE}/base:${BASE}
	docker images | grep ${DOCKER_IMAGE}/base | grep ${BASE}

build: ## Builds the image
	cd .. && docker build \
		${BUILD_OPTIONS} \
		--platform linux/amd64 \
		--progress plain \
		--build-arg VERSION="${VERSION}" \
		--build-arg BASE_IMAGE="${BASE}" \
		--build-arg DOCKER_REGISTRY="${DOCKER_REGISTRY}" \
		-t ${DOCKER_IMAGE_FULLNAME} \
		-f docker/Dockerfile .
	@docker images | grep ${DOCKER_IMAGE} | grep ${VERSION}

registrylogin:  ## Log in to docker
	@echo ${DOCKER_SECRET} | echo docker login ${DOCKER_REGISTRY} -u ${DOCKER_USERNAME} --password-stdin ; \

release:  ## For now manual release until we fix nexus
	scp -o ProxyJump=kjump ../dist/image-${CONTAINER_NAME}-${VERSION}.tgz khetz:/tmp

#release: registrylogin  ## Release the image
#	# docker push ${DOCKER_REGISTRY}/${DOCKER_IMAGE}/base:${BASE}
#	docker push ${DOCKER_IMAGE_FULLNAME}
#	docker images | grep ${DOCKER_IMAGE}
#
#nexus-release:
#	docker tag ${DOCKER_IMAGE_FULLNAME} docker.singlewave.co.uk/${DOCKER_IMAGE}:${VERSION}
#	docker push docker.singlewave.co.uk/${DOCKER_IMAGE}:${VERSION}

release-all: release nexus-release

full-release:  build-base build release  ## buils all and releases
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
			-p ${LOCAL_PORT}:8000 \
			-p ${LOCAL_HTTPS_PORT}:8443 \
			-e DJANGO_SETTINGS_MODULE="krm3.config.settings" \
			-e KRM3_DEBUG="${KRM3_DEBUG}" \
			-e KRM3_DATABASE_URL="${KRM3_DATABASE_URL}" \
			-e KRM3_DATABASE_APPS="${KRM3_DATABASE_APPS}" \
			-e KRM3_SECRET_KEY="${KRM3_SECRET_KEY}" \
			-e KRM3_ADMIN_EMAIL="${KRM3_ADMIN_EMAIL}" \
			-e KRM3_ADMIN_USERNAME="${KRM3_ADMIN_USERNAME}" \
			-e KRM3_ADMIN_PASSWORD="${KRM3_ADMIN_PASSWORD}" \
			-e KRM3_STATIC_ROOT="/tmp/static" \
			-e KRM3_MEDIA_ROOT="/tmp/media" \
			-e STACK_PROTOCOL=${STACK_PROTOCOL} \
			-e KRM3_ALLOWED_HOSTS=krm3.k-tech.it,krm3.local \
			-v "`pwd`/certs:/etc/certs:ro" \
			-v "/etc/ssl/certs:/etc/ssl/certs:ro" \
			${RUN_OPTIONS} \
			${DOCKER_IMAGE_FULLNAME} \
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

stack:  ## run containder with both web/celery services
	RUN_OPTIONS=-it CMD='stack' $(MAKE) .run

save:
	@mkdir -p ../dist
	@echo "Saving image ../dist/image-${CONTAINER_NAME}-${VERSION}.tgz"
	@docker save ${DOCKER_IMAGE_FULLNAME} | gzip > ../dist/image-${CONTAINER_NAME}-${VERSION}.tgz
	@echo "Now you can run:"
	@echo "  scp -o ProxyJump=kjump ../dist/image-${CONTAINER_NAME}-${VERSION}.tgz khetz:/tmp"
	@echo "And on the server:"
	@echo "  docker load -i /tmp/image-${CONTAINER_NAME}-${VERSION}.tgz && rm /tmp/image-${CONTAINER_NAME}-${VERSION}.tgz"
