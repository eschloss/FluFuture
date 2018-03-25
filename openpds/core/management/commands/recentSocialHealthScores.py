from django.core.management.base import BaseCommand
import logging
from openpds.questions.socialhealth_tasks import recentSocialHealthScores

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        logging.info("@@---- Starting Social Health Scores Command ----@@")
        recentSocialHealthScores.delay()
