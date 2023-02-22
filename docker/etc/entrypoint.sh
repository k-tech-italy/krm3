#!/bin/bash -e

STATIC_ROOT=KRM3_STATIC_ROOT
MEDIA_ROOT=KRM3_MEDIA_ROOT
ADMIN_USERNAME=KRM3_ADMIN_USERNAME
ADMIN_EMAIL=KRM3_ADMIN_EMAIL
ADMIN_PASSWORD=KRM3_ADMIN_PASSWORD
CELERY_BROKER_URL=KRM3_CELERY_BROKER_URL

mkdir -p "/krm3/logs" "${STATIC_ROOT}" "${MEDIA_ROOT}"
chown krm3 -R /krm3 "${STATIC_ROOT}" "${MEDIA_ROOT}"

setup() {
  gosu krm3 django-admin upgrade -vv \
          --admin-username ${ADMIN_USERNAME:-admin} \
          --admin-email ${ADMIN_EMAIL} \
          --admin-password ${ADMIN_PASSWORD}
}
if [ "${STACK_PROTOCOL}" = "https" ]; then
      echo "setting up HTTPS"
      STACK_PORT="8443,/etc/certs/cbtcsudan.crt,/etc/certs/cbtcsudan.key"
else
      echo "setting up HTTP"
      STACK_PORT=8000
fi

if [ "$*" = "run" ]; then
  setup
  exec gosu krm3 uwsgi --${STACK_PROTOCOL} 0.0.0.0:${STACK_PORT} \
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
  export STACK_PROTOCOL
  export STACK_PORT
  exec gosu krm3 circusd /etc/circus.conf
elif [ "$*" = "dev" ]; then
  setup
  exec gosu krm3 django-admin runserver 0.0.0.0:8000
elif [ "$*" = "flower" ]; then
  exec gosu krm3 -A krm3.config.celery --broker=${CELERY_BROKER_URL} flower
elif [ "$*" = "beat" ]; then
  setup
  celery -A krm3.config.celery beat --loglevel=INFO
else
  exec "$@"
fi
