from django.core.management.base import BaseCommand
import logging
from openpds.questions.tasks import howAreYouFeelingTodayAllUsers

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        howAreYouFeelingTodayAllUsers.delay()
