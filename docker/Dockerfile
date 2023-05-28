ARG BASE_IMAGE
ARG DOCKER_REGISTRY

FROM ${DOCKER_REGISTRY}/kt/krm3/base:${BASE_IMAGE}

ENV DJANGO_SETTINGS_MODULE="krm3.config.settings" \
	KRM3_MEDIA_ROOT="/tmp/media" \
    KRM3_ADMIN_EMAIL="" \
    KRM3_ADMIN_PASSWORD="" \
    KRM3_ADMIN_USERNAME="" \
    KRM3_CELERY_BROKER="" \
    KRM3_DATABASE_URL="" \
    KRM3_REDIS_CACHE_URL="" \
    KRM3_SECRET_KEY="" \
    KRM3_STATIC_ROOT="/tmp/static"


WORKDIR /code

RUN sha1sum -c /CHECKSUM

ADD . /code

RUN chown -R krm3:ktech /code/*

USER krm3

SHELL ["/bin/bash", "-c"]

ADD tools/zapdata/demo tools/zapdata/demo
RUN pip install . --no-deps -vv && rm -fr src dist docker
