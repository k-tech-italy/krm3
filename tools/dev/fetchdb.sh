#!/bin/bash

### ND: needs pgpass to be setup
DB_ENGINE=`python manage.py shell --no-imports -c "from django.conf import settings; print(settings.DATABASES['default']['ENGINE'])"`
DB_HOST=`python manage.py shell --no-imports -c "from django.conf import settings; print(settings.DATABASES['default']['HOST'])"`
DB_PORT=`python manage.py shell --no-imports -c "from django.conf import settings; print(settings.DATABASES['default']['PORT'], end='')"`
DB_NAME=`python manage.py shell --no-imports -c "from django.conf import settings; print(settings.DATABASES['default']['NAME'], end='')"`
echo "Initialising DB ${DB_NAME}"

echo Deleting database "${DB_NAME}"
psql -h ${DB_HOST} -p ${DB_PORT} -U postgres -c "DROP DATABASE IF EXISTS ${DB_NAME}"
psql -h ${DB_HOST} -p ${DB_PORT} -U postgres -c "CREATE DATABASE ${DB_NAME}"

pg_dump -p 16432 -h localhost -U postgres -d krm3 -O -x | psql -h localhost -p ${DB_PORT} -U postgres --set ON_ERROR_STOP=on -d ${DB_NAME}

DJANGO_SUPERUSER_PASSWORD=123 ./manage.py createsuperuser --username admin --email a@a.com --noinput
