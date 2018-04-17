from django.core.management.base import BaseCommand
import datetime
import heroku3
import os

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        HEROKU_API_KEY = os.environ['HEROKU_API_KEY']
        APP_NAME = os.environ['APP_NAME']
        heroku_conn = heroku3.from_key(HEROKU_API_KEY)
        app = heroku_conn.apps()[APP_NAME]
        app.restart()
