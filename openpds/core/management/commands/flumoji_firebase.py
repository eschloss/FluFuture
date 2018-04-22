from django.core.management.base import BaseCommand
import logging
from openpds.questions.tasks import howAreYouFeelingTodayAllUsers, flumojiNotifications
from django.db import connection
from openpds.questions.socialhealth_tasks import recentSocialHealthScores
from pyfcm import FCMNotification
from openpds.settings import FCM_SERVER_KEY
from openpds.core.models import FirebaseToken

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        #howAreYouFeelingTodayAllUsers.delay()
        #flumojiNotifications.delay()

        fts = FirebaseToken.objects.filter(old=False)
        push_service = FCMNotification(api_key=FCM_SERVER_KEY)
        
        # Send to multiple devices by passing a list of ids.
        registration_ids = fts.values_list("token", flat=True)
        message_title = "LiverSmart"
        message_body = "How are you feeling?"
        result = push_service.notify_multiple_devices(registration_ids=registration_ids, message_title=message_title, message_body=message_body)
        
        #temp bug fix
        with connection.cursor() as cursor:
            cursor.execute("truncate table celery_taskmeta")
        
