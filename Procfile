web: bin/start-nginx bin/start-pgbouncer-stunnel newrelic-admin run-program uwsgi uwsgi.ini
worker: python manage.py celery worker -l info --without-gossip --autoscale=30,2