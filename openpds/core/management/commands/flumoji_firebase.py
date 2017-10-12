from django.core.management.base import BaseCommand
import logging
from openpds.questions.tasks import howAreYouFeelingTodayAllUsers, flumojiNotifications

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        #howAreYouFeelingTodayAllUsers.delay()
        flumojiNotifications.delay()
