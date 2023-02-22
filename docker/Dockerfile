ARG BASE_IMAGE
ARG DOCKER_REGISTRY
FROM ${DOCKER_REGISTRY}/wfp/krm3/base:${BASE_IMAGE}

ENV DJANGO_SETTINGS_MODULE="krm3.config.settings" \
	KRM3MEDIA_ROOT="/tmp/media" \
    KRM3ADMIN_EMAIL="" \
    KRM3ADMIN_PASSWORD="" \
    KRM3ADMIN_USERNAME="" \
    KRM3CELERY_BROKER="" \
    KRM3DATABASE_URL="" \
    KRM3MINIO_CONF_VALIDATION="" \
    KRM3MINIO_ENDPOINT_URL="" \
    KRM3MINIO_PORT="" \
    KRM3MINIO_SECURE="" \
    KRM3REDIS_CACHE_URL="" \
    KRM3SECRET_KEY="" \
    KRM3STATIC_ROOT="/tmp/static"

EXPOSE 8000
EXPOSE 8443
ADD . /code
WORKDIR /code
VOLUME /etc/certs

RUN sha1sum -c /CHECKSUM
RUN pip install . --no-deps -vv \
    && rm -fr /code

COPY docker/etc/entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY docker/etc/circus.conf /etc/circus.conf


ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["stack"]
