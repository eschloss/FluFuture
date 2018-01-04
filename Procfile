web: bin/start-nginx bin/start-pgbouncer-stunnel newrelic-admin run-program uwsgi uwsgi.ini
worker: bin/start-pgbouncer-stunnel  python manage.py celery worker -B -l info
