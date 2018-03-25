from django.core.management.base import BaseCommand
import logging
from openpds.questions.tasks import howAreYouFeelingTodayAllUsers, flumojiNotifications
from django.db import connection
from openpds.questions.socialhealth_tasks import recentSocialHealthScores

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        #howAreYouFeelingTodayAllUsers.delay()
        flumojiNotifications.delay()
        
        #temp bug fix
        with connection.cursor() as cursor:
            cursor.execute("truncate table celery_taskmeta")
        
