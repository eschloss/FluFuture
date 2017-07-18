from django.shortcuts import render_to_response
from django.template import RequestContext
import pdb
from openpds.visualization.internal import getInternalDataStore
from openpds.core.models import Profile, FluQuestions, ProfileStartEnd, FB_Connection, Emoji, Emoji2, emoji_choices, QuestionInstance, QuestionType, FirebaseToken, IPReferral
import facebook
import json, datetime, time, re, math, pytz
from django.http import HttpResponse, Http404, HttpResponseRedirect, HttpResponseForbidden
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from calendar import monthrange
from openpds.questions.tasks import checkForProfileReferral
from django.views.decorators.cache import cache_page
from pymongo import Connection
import random
from django.conf import settings

def dupEmojis(request):
    for e in Emoji.objects.all():
        Emoji2.objects.create(profile=e.profile, emoji=e.emoji, created=e.created, lat=e.lat, lng=e.lng)
    return HttpResponse("success")
    
def getLength(request):
    
    connection = Connection(
        host=random.choice(getattr(settings, "MONGODB_HOST", None)),
        port=getattr(settings, "MONGODB_PORT", None),
        readPreference='nearest'
    )
    
    for p in Profile.objects.all():
        pse = ProfileStartEnd.objects.filter(profile=p)
        if len(pse) == 0:
            dbName = p.getDBName().strip()
            try:
                db = connection[dbName]
                collection = db["funf"]
                try:
                    count = db.command("collstats", "funf")["count"]
                    if count == 0:
                        ProfileStartEnd.objects.create(profile=p)
                    else:
                        start = collection.find({"key": {"$ne": "edu.mit.media.funf.probe.builtin.WifiProbe"}}).sort("time", 1)[0]["time"]
                        end = collection.find({"key": {"$ne": "edu.mit.media.funf.probe.builtin.WifiProbe"}}).sort("time", -1)[0]["time"]
                        # TODO NExt time don't use wifiProbe timestamps (or SMS) it's unreliable - probably ActivityProbe or screenProbe
                        # also must check to make sure the start time is after profile.created
                        
                        days = end - start
                        days = int(days / 60.0 / 60.0/ 24.0)
                        
                        ProfileStartEnd.objects.create(profile=p, start=datetime.datetime.fromtimestamp(start), end=datetime.datetime.fromtimestamp(end), days=days)
                except:
                    pass
            except:
                pass
    connection.close()
    return HttpResponse("success")

def removeEmptyPSE(request):
    pses = ProfileStartEnd.objects.filter(start__isnull=True) | ProfileStartEnd.objects.filter(end__isnull=True)
    
def getEmoji(n):
    for x in EMOJI_PERCENTAGE_CUMULATIVE:
        if n < x[1]:
            return x[0]
    return 'h'
    
EMOJI_PERCENTAGE = {
    'h':  .16, # 'healthy':  
    's':  .08, # 'sick':  
    'y':  .13, # 'sleepy':  
    'c':  .05, # 'cough':  
    'f':  .05, # 'fever':  
    'u':  .015, # 'flu':  
    'n':  .04, # 'nauseous':  
    'l':  .04, # 'sore throat':  
    'r':  .08, # 'runnynose':  
    'b':  .01, # 'body ache':  
    'a':  .08, #'calm':  
    'd':  .065, #'down':  
    'e':  .1, #'energized':  
    'm':  .03, #'motivated':  
    't':  .07, #'trouble concentrating':  
}
EMOJI_PERCENTAGE_CUMULATIVE = [
      (    'h',  .16,   ),  # 'healthy',  
      (    's',  .24,   ),  # 'sick',  
      (    'y',  .37,   ),  # 'sleepy',  
      (    'c',  .42,   ),  # 'cough',  
      (    'f',  .47,   ),  # 'fever',  
      (    'u',  .485,   ),  # 'flu',  
      (    'n',  .525,   ),  # 'nauseous',  
      (    'l',  .565,   ),  # 'sore throat',  
      (    'r',  .645,   ),  # 'runnynose',  
      (    'b',  .655,   ),  # 'body ache',  
      (    'a',  .735,   ),  #'calm',  
      (    'd',  .8,   ),  #'down',  
      (    'e',  .9,   ),  #'energized',  
      (    'm',  .93,   ),  #'motivated',  
      (    't',  1.0,   ),  #'trouble concentrating',  
]
    
def randEmojis(request):
    pses = ProfileStartEnd.objects.filter(days__gt=2)
    totalcreated = 0
    for pse in pses:
        start = pse.start
        new_start = datetime.datetime(2017,2,29)
        if new_start > start:
            start = new_start
        end = pse.end
        if start > end:
            continue
        
        randint = random.randint(3,5)
        count = 1
        start = start + datetime.timedelta(days=randint)
        while start < end:
            emojinum = random.random()
            emoji = getEmoji(emojinum) #todo Hard - should be some correlation
            Emoji2.objects.create(profile=pse.profile, created=start, emoji=emoji)
            totalcreated += 1
            randint = random.randint(3,5 + count)
            count += 1
            start = start + datetime.timedelta(days=randint)
            rmin = random.randint(0, 60)
            rsec = random.randint(0, 60)
            msec = random.randint(0, 1000000)
            rhour = random.randint(9, 18)
            start = start.replace(hour=rhour, minute=rmin, second=rsec, microsecond=msec)
            
    return HttpResponse(str(totalcreated))
    
def fluQuestionSet(request):
    ps = Profile.objects.all()
    for p in ps:
        if FluQuestions.objects.filter(profile=p).count() == 0:
            r1 = random.random() < .05 # get flu this season yet
            r2 = random.random() < .17 # get flu last season
            r3 = random.random() < .35 # vaccine this season
            if Emoji2.objects.filter(emoji='u', profile=p).count() > 0:
                r3 = False
            FluQuestions.objects.create(profile=p, fluThisSeason=r1, fluLastSeason=r2, vaccineThisSeason=r3)
    return HttpResponse("Success")
            
            