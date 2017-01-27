from django.core.management.base import BaseCommand
import logging
from openpds.questions.socialhealth_tasks import recentSocialHealthScores
from openpds.questions.tasks import ensureFunfIndexes, recentProbeCounts, dumpFunfData, dumpSurveyData, flumojiNotifications, emojiLocations, deleteUnusedProfiles, profileLocations, setInfluenceScores, cleanExpiredReferrals

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        #flumojiNotifications.delay()
        recentProbeCounts.delay()
        #recentSocialHealthScores.delay()
        ensureFunfIndexes.delay()
        dumpFunfData.delay()
        #dumpSurveyData.delay()
        emojiLocations.delay()
        profileLocations.delay()
        #deleteUnusedProfiles.delay()
        setInfluenceScores.delay()
        cleanExpiredReferrals.delay()
