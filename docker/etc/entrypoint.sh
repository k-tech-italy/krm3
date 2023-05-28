#!/bin/bash -e

STATIC_ROOT=${KRM3_STATIC_ROOT}
MEDIA_ROOT=${KRM3_MEDIA_ROOT}
CELERY_BROKER_URL=${KRM3_CELERY_BROKER_URL}
STACK_PROTOCOL=${KRM3_STACK_PROTOCOL:-http}

mkdir -p "/krm3/logs" "${STATIC_ROOT}" "${MEDIA_ROOT}"


setup() {
  django-admin upgrade -vv --no-input \
          --static \
          --admin-username ${KRM3_ADMIN_USERNAME:-admin} \
          --admin-email "${KRM3_ADMIN_EMAIL:-noreply@k-tech.it}" \
          --admin-password ${KRM3_ADMIN_PASSWORD:-admin}
}
if [ "${STACK_PROTOCOL}" = "https" ]; then
      echo "setting up HTTPS"
      STACK_PORT="8443,/etc/certs/server.crt,/etc/certs/server.key"
else
      echo "setting up HTTP"
      STACK_PORT=8000
fi

if [ "$*" = "run" ]; then
  setup
  exec uwsgi --${STACK_PROTOCOL} 0.0.0.0:${STACK_PORT} \
    --static-map "/static=$KRM3_STATIC_ROOT" \
    --static-map "/media=$KRM3_MEDIA_ROOT" \
    --master \
    --module krm3.config.wsgi \
    --processes 4 \
    --offload-threads 8
elif [ "$*" = "worker" ]; then
  setup
  celery -A krm3.config.celery worker --loglevel=INFO  -n wk_%h
elif [ "$*" = "stack" ]; then
  setup
  export STACK_PROTOCOL=${STACK_PROTOCOL}
  export STACK_PORT=${STACK_PORT}
  exec circusd /etc/circus.conf
elif [ "$*" = "dev" ]; then
  setup
  exec django-admin runserver 0.0.0.0:8000
elif [ "$*" = "flower" ]; then
  exec -A krm3.config.celery --broker=${CELERY_BROKER_URL} flower
elif [ "$*" = "beat" ]; then
  setup
  celery -A krm3.config.celery beat --loglevel=INFO
else
  exec "$@"
fi
