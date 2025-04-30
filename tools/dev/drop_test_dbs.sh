#!/bin/bash

### ND: needs pgpass to be setup
DB_ENGINE=`python manage.py shell --no-imports -c "from django.conf import settings; print(settings.DATABASES['default']['ENGINE'])"`
DB_HOST=`python manage.py shell --no-imports -c "from django.conf import settings; print(settings.DATABASES['default']['HOST'])"`
DB_PORT=`python manage.py shell --no-imports -c "from django.conf import settings; print(settings.DATABASES['default']['PORT'], end='')"`
DB_NAME=`python manage.py shell --no-imports -c "from django.conf import settings; print(settings.DATABASES['default']['NAME'], end='')"`


test_databases_file=/tmp/test_dbs.txt
psql -h ${DB_HOST} -p ${DB_PORT} -U postgres -d postgres -c "SELECT datname FROM pg_database WHERE datname LIKE 'test_%' AND datistemplate=false" | grep -e "^ test_.*" > $test_databases_file

while read dbname
do
  echo "dropping DB $dbname..."
  dropdb -h ${DB_HOST} -p ${DB_PORT} -U postgres "$dbname"
done < $test_databases_file

echo "removing $test_databases_file file"
#rm $test_databases_file

echo "dropping DB test_${DB_NAME} DB"
dropdb -h ${DB_HOST} -p ${DB_PORT} -U postgres "test_${DB_NAME}"
