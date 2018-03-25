from django.core.management.base import BaseCommand
import logging
from socialhealth_tasks import recentSocialHealthScores

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        recentSocialHealthScores.delay()
