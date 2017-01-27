web: bin/start-nginx bin/start-pgbouncer-stunnel newrelic-admin run-program uwsgi uwsgi.ini
worker: newrelic-admin run-program python manage.py celery worker -B -l info
