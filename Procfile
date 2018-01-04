web: bin/start-nginx bin/start-pgbouncer-stunnel uwsgi uwsgi.ini
worker: bin/start-pgbouncer-stunnel python manage.py celery worker -B -l info
