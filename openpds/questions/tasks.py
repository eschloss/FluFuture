from celery import task
from openpds.core.models import IPReferral, Profile, Emoji, Notification, Device, QuestionInstance, QuestionType
from bson import ObjectId
from pymongo import Connection
from django.conf import settings
import time
from datetime import date, timedelta, datetime
import json
import pdb
from gcm import GCM
from SPARQLWrapper import SPARQLWrapper, JSON
from collections import Counter
import sqlite3
import random
from openpds.questions.socialhealth_tasks import getStartTime
from openpds import getInternalDataStore

"""
connection = Connection(
    host=random.choice(getattr(settings, "MONGODB_HOST", None)),
    port=getattr(settings, "MONGODB_PORT", None),
    readPreference='nearest'
)
"""

@task()
def ensureFunfIndexes():
    profiles = Profile.objects.all()

    for profile in profiles:
        ensureFunfIndex.delay(profile.pk)
        
@task()
def ensureFunfIndex(pk):
    profile = Profile.objects.get(pk=pk)
    dbName = profile.getDBName()
    
    connection = Connection(
        host=random.choice(getattr(settings, "MONGODB_HOST", None)),
        port=getattr(settings, "MONGODB_PORT", None),
        readPreference='nearest'
    )
    try:
        connection.admin.command('enablesharding', dbName)
    except:
        pass
    collection = connection[dbName]["funf"]
    
    collection.ensure_index([("time", -1), ("key", 1)], cache_for=7200, background=True, unique=True, dropDups=True)
    connection.close()
    

#this might be causing a bug so i removed it from openpds_scheduled_tasts.py
@task()
def deleteUnusedProfiles():
    profiles = Profile.objects.all()

    for profile in profiles:
        deleteUnusedProfile.delay(profile.pk)

#deprecated - do not use this
@task()
def deleteUnusedProfile(pk):
    #start = getStartTime(60, False)
    profile = Profile.objects.get(pk=pk)
    dbName = profile.getDBName()
    
    connection = Connection(
        host=random.choice(getattr(settings, "MONGODB_HOST", None)),
        port=getattr(settings, "MONGODB_PORT", None),
        readPreference='nearest'
    )
    db = connection[dbName]#["funf"]
    
    #if collection.find({"time": { "$gte": start}}).count() == 0:
    if 'funf' not in db.collection_names(): 
        connection.drop_database(dbName)
        if Emoji.objects.filter(profile=profile).count() == 0 and not profile.fbid and not profile.referral:
            profile.delete()
    connection.close()

@task()
def recentProbeCounts():
    profiles = Profile.objects.all()
    for profile in profiles:
        recentProbeCounts2.delay(profile.pk)
        
@task()
def recentProbeCounts2(pk):
    startTime = getStartTime(1, False)
    profile = Profile.objects.get(pk=pk)
    ids = getInternalDataStore(profile, "", "Living Lab", "")
    probes = ["ActivityProbe", "SimpleLocationProbe", "CallLogProbe", "SmsProbe", "WifiProbe", "BluetoothProbe"]
    answer = {}
    for probe in probes:
        data = ids.getData(probe, startTime, None)
        answer[probe] = data.count()
    ids.saveAnswer("RecentProbeCounts", answer)
    

def addNotification(profile, notificationType, title, content, uri):
    notification, created = Notification.objects.get_or_create(datastore_owner=profile, type=notificationType)
    notification.title = title
    notification.content = content
    notification.datastore_owner = profile
    if uri is not None:
        notification.uri = uri
    notification.save()

def addNotificationAndNotify(profile, notificationType, title, content, uri):
    addNotification(profile, notificationType, title, content, uri)
    if Device.objects.filter(datastore_owner = profile).count() > 0:
        gcm = GCM(settings.GCM_API_KEY)

        for device in Device.objects.filter(datastore_owner = profile):
            try:
                gcm.plaintext_request(registration_id=device.gcm_reg_id, data= {"action":"notify"})
            except Exception as e:
                print "Issue with sending notification to: %s, %s" % (profile.id, profile.uuid)
                print e

def notifyAll():
    for profile in Profile.objects.all():
        if Device.objects.filter(datastore_owner = profile).count() > 0:
            gcm = GCM(settings.GCM_API_KEY)
            for device in Device.objects.filter(datastore_owner = profile):
                try:
                    gcm.plaintext_request(registration_id=device.gcm_reg_id, data={"action":"notify"})
                except Exception as e:
                    print "Issue with sending notification to: %s, %s" % (profile.id, profile.uuid)
                    print e

def broadcastNotification(notificationType, title, content, uri):
    for profile in Profile.objects.all():
        addNotificationAndNotify(profile, notificationType, title, content, uri)

@task()
def sendVerificationSurvey():
    broadcastNotification(2, "Social Health Survey", "Please take a moment to complete this social health survey", "/survey/?survey=8")

@task()
def sendPast3DaysSurvey():
    broadcastNotification(2, "Social Health Survey", "Please take a moment to complete this social health survey", "/survey/?survey=5")

@task()
def sendExperienceSampleSurvey():
    broadcastNotification(2, "Social Health Survey", "Please take a moment to complete this social health survey", "/survey/?survey=9")

@task()
def sendSleepStartSurvey():
    broadcastNotification(2, "Sleep Tracker", "Please take this survey right before bed", "/survey/?survey=10")

@task()
def sendSleepEndSurvey():
    broadcastNotification(2, "Sleep Tracker", "Please take this survey right after waking up", "/survey/?survey=11")

def minDiff(elements, item):
    return min([abs(el - item) for el in elements])

@task()
def scheduleExperienceSamplesForToday():
    # We're scheduling 4 surveys / day, starting in the morning, with at least an hour of time in between each
    # assuming we send the first within 2 hours of running this, and need to get all surveys done within 8 hours,
    # we can build the list of delays via simple rejection  
    maxDelay = 3600 * 8
    delays = [random.randint(0,maxDelay)]
    while len(delays) < 4:
        nextDelay = random.randint(0, maxDelay)
        if minDiff(delays, nextDelay) >= 3600:
            delays.append(nextDelay)
    print delays
    print [time.strftime("%H:%M", time.localtime(1385042444 + d)) for d in delays]
    for t in delays:
        print "sending survey with %s second delay..." % str(t)
        sendExperienceSampleSurvey.apply_async(countdown = t)

@task() 
def findMusicGenres():
    profiles = Profile.objects.all()
    sparql = SPARQLWrapper("http://dbpedia.org/sparql")
    sparql.setReturnFormat(JSON)
    artistQuery = "PREFIX dbpprop: <http://dbpedia.org/property/> PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> select ?artist ?genre from <http://dbpedia.org> where { ?artist rdfs:label \"%s\"@en . ?artist dbpprop:genre ?genre }" 
    albumQuery = "PREFIX dbpedia-owl: <http://dbpedia.org/ontology/> PREFIX dbpprop: <http://dbpedia.org/property/> select ?album ?genre from  <http://dbpedia.org> where { ?album a dbpedia-owl:Album . ?album dbpprop:name '%s'@en . ?album dbpprop:genre ?genre }"

    for profile in profiles:
        dbName = profile.getDBName()
        
        connection = Connection(
            host=random.choice(getattr(settings, "MONGODB_HOST", None)),
            port=getattr(settings, "MONGODB_PORT", None),
            readPreference='nearest'
        )
        answerListCollection = connection[dbName]["answerlist"]
        collection = connection[dbName]["funf"]
        
        songs = [song["value"] for song in collection.find({ "key": { "$regex": "AudioMediaProbe$"}})]
        artists = set([str(song["artist"]) for song in songs if str(song["artist"]) != "<unkown>" and '"' not in str(song["artist"])])
#        albums = set([str(song["album"]) for song in songs if str(song["album"]) != "<unknown>" and '"' not in str(song["album"])])
        genres = []
        for artist in artists:
            temp = artistQuery % artist
            print temp
            sparql.setQuery(temp)
            results = sparql.query().convert()
            genres.extend([binding["genre"]["value"] for binding in results["results"]["bindings"]])
#        for album in albums:
#            temp = albumQuery % album
#            print temp
#            sparql.setQuery(temp)
#            results = sparql.query().convert()
#            genres.extend([binding["genre"]["value"] for binding in results["results"]["bindings"]])
        if len(genres) > 0:
            counts = Counter(genres).most_common(10)
            musicGenres = answerListCollection.find({ "key": "MusicGenres" })
            musicGenres = musicGenres[0] if musicGenres.count() > 0 else { "key": "MusicGenres", "value": [] }
            musicGenres["value"] = [count[0] for count in counts]
            answerListCollection.save(musicGenres)
        connection.close()


@task()
def dumpFunfData():
    profiles = Profile.objects.all()
    for profile in profiles:
        dumpFunfData2.delay(profile.pk)
    
@task()
def dumpFunfData2(pk):
    outputConnection = sqlite3.connect("openpds/static/dump.db")
    c = outputConnection.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS funf (user_id integer, key text, time real, value text, PRIMARY KEY (user_id, key, time) on conflict ignore)")
    startTime = getStartTime(3, False)#max(1378008000, startTimeRow[0]) if startTimeRow is not None else 1378008000
    
    profile = Profile.objects.get(pk=pk)
    dbName = profile.getDBName()
    
    connection = Connection(
        host=random.choice(getattr(settings, "MONGODB_HOST", None)),
        port=getattr(settings, "MONGODB_PORT", None),
        readPreference='nearest'
    )
    try:
        connection.admin.command('enablesharding', dbName)
    except:
        pass
    funf = connection[dbName]["funf"]
    
    user = int(profile.id)
    c.executemany("INSERT INTO funf VALUES (?,?,?,?)", [(user,d["key"][d["key"].rfind(".")+1:],d["time"],"%s"%d["value"]) for d in funf.find({"time": {"$gte": startTime}}) if d["key"] is not None])

    outputConnection.commit()
    outputConnection.close()
    connection.close()

@task()
def dumpSurveyData():
    profiles = Profile.objects.all()
    outputConnection = sqlite3.connect("openpds/static/dump.db")
    c = outputConnection.cursor()
    #c.execute("DROP TABLE IF EXISTS survey;")
    c.execute("CREATE TABLE IF NOT EXISTS survey (user_id integer, key text, time real, value text, PRIMARY KEY (user_id, key, time) on conflict ignore);")

    for profile in profiles:
        dbName = profile.getDBName()
        
        connection = Connection(
            host=random.choice(getattr(settings, "MONGODB_HOST", None)),
            port=getattr(settings, "MONGODB_PORT", None),
            readPreference='nearest'
        )
        try:
            connection.admin.command('enablesharding', dbName)
        except:
            pass
        answerlist = connection[dbName]["answerlist"]
        user = int(profile.id)
        for datum in answerlist.find({ "key": { "$regex": "Past3Days$"}}):
            for answer in datum["value"]:
                #print type(user), type(datum["key"]), type(answer)#, type(datum["value"])
                c.execute("INSERT INTO survey VALUES (?,?,?,?);", (user,datum["key"],answer["time"],"%s"%answer["value"]))
        for datum in answerlist.find({ "key": { "$regex": "Verification"}}):
            for answer in datum["value"]:
                c.execute("INSERT INTO survey VALUES (?,?,?,?);", (user,datum["key"],answer["time"],"%s"%answer["value"]))
        for datum in answerlist.find({ "key": { "$regex": "Last15Minutes"}}):
            for answer in datum["value"]:
                c.execute("INSERT INTO survey VALUES (?,?,?,?);", (user,datum["key"],answer["time"],"%s"%answer["value"]))
        connection.close()
    outputConnection.commit()
    outputConnection.close()

def addNotification(profile, notificationType, title, content, uri):
    notification, created = Notification.objects.get_or_create(datastore_owner=profile, type=notificationType)
    if uri != -1:
        notification.title = uri # Set title as URI for now
    notification.content = content
    notification.datastore_owner = profile
    if uri is not None:
        notification.uri = uri
    notification.save()


# formats a notification the way the SmartCATCH client understands it
def formatNotification(question, type="Picker", description="", items=[], **kwargs):
    s1 = "<startTitle>" + question + "<endTitle><startType>" + type + "<endType><startDescription>" + description + "<endDescription>"
    s2 = "<startNumItems>%d<endNumItems>" % len(items) + ''.join(["<startI%d>%s<endI%d>" % (i+1,items[i],i+1) for i in xrange(len(items))])
    s3 = "<startNegButton>Delay<endNegButton><startPosButton>Submit<endPosButton><startNumRepeats>3<endNumRepeats><startTimeRepeat>5000<endTimeRepeat>" # TODO: format this. Unclear about this param$

    return json.dumps({ 's1': s1, 's2': s2, 's3': s3 })
#    return s1, s2, s3 # TODO: JSONfy

def fetchQuestion(profile, device):
    ret_val = None
    q_list = []

    qtypes = QuestionType.objects.filter(frequency_interval__isnull=False, frequency_interval__lt=5256000)
    qtypes = qtypes.filter(goal__isnull=True) | qtypes.filter(goal=profile.goal)

    print "DEBUG: got %d question types" % qtypes.count()
    for qtype in qtypes:
        # Get previous recent questions asked

        # TODO: d needs to be based on wakeup time of the current user, and not on NOW.
#        d = date.today() - timedelta(minutes=qtype.frequency_interval)
#        questions = QuestionInstance.objects.filter(profile=profile).filter(datetime__gt=d).filter(question_type=qtype) # TODO: probably need an index: (profile, datetime).

        questions = QuestionInstance.objects.filter(profile=profile).filter(question_type=qtype).filter(expired=False)

        print "QUESTIONS = %s" % questions

        if qtype.sleep_offset < 0:
            d_ask = datetime.combine(datetime.date(datetime.today()), profile.sleep) - timedelta(qtype.sleep_offset)
        else:
            d_ask = datetime.combine(datetime.date(datetime.today()), profile.wake) + timedelta(qtype.sleep_offset)
        if (questions.count() == 0 and d_ask.time() < datetime.time(datetime.now()) ):
            # this question wasn't asked yet. Generate it.
            q = QuestionInstance(question_type=qtype, profile=profile)
            q_list.append({'instance': q, 'type': qtype})

            qf = None
            if qtype.followup_question:
                # generate the data question as well
                qf = QuestionInstance(question_type=qtype.followup_question, profile=profile)
                q.notification_counter = 1

            q.save()
            if qf:
                qf.save()
        else:
            ql = list(questions.reverse()[:1])
            q = None
            if ql:
                q = ql[0]

            if (q and qtype.resend_quantity > q.notification_counter):
                # Check if q needs to be reasked and act accordingly
                next_qtime = q.datetime + timedelta(minutes=REPEAT_INTERVAL)
                if (next_qtime < timezone.now()):
                    if not q.answer or (qtype.followup_key != None and q.answer != qtype.followup_key):
                        print 'Updating question = %s' % q
                        q.notification_counter = q.notification_counter + 1
                        q.save()
                        q_list.append({'instance': q, 'type': qtype})

    # at this point q_list contains notification questions (not followups)
    if len(q_list) > 1:
        ret_val = {'question': ('You have %d unanswered questions' % len(q_list)), 'description': 'Multiple questions', 'action': -1}
    elif len(q_list) == 1:
        ret_val = {'question': q_list[0]['type'].text, 'description': q_list[0]['type'].text, 'action': q_list[0]['instance'].id}

    return ret_val

def expireQuestions():
    questions = QuestionInstance.objects.all().filter(expired=False)
    for question in questions:
        dt = timezone.now() - timedelta(minutes=question.question_type.expiry)
        if ( dt > question.datetime ):
            # This question is expired. Update it
            question.expired = True
            print "Expiring question %d" % question.id
            question.save()

@task()
def flumojiNotifications():
    print "Starting notifications task"
    expireQuestions()

    profiles = Profile.objects.all()
    for profile in profiles:

        if Device.objects.filter(datastore_owner = profile).count() > 0:
            gcm = GCM(settings.GCM_API_KEY)
            for device in Device.objects.filter(datastore_owner = profile):
                try:
                    # add the notification to the D
                    q_params = fetchQuestion(profile, device)
                except Exception as e:
                    print "NotificationError1: Issue with sending notification to: %s, %s" % (profile.id, profile.uuid)
                    print e
                    
                try:
                    print 'q_params = %s' % q_params
                    if q_params is not None:
                        js = formatNotification(q_params['question'],
                                                description=q_params['description'],
                                                items=[q_params['action']])
                        addNotification(profile, 2, 'SmartCATCH',
                                        q_params['question'],
                                        q_params['action'])
                        # send an alert that a notification is ready (app will call back to fetch the notification data)
                        print "id=%s, uuid=%s, device=%s" % (profile.id, profile.uuid,device.gcm_reg_id)
                        gcm.plaintext_request(registration_id=device.gcm_reg_id,
                                              data={"action":"notify"},
                                              collapse_key=q_params['question'])
                except Exception as e:
                    print "NotificationError2: Issue with sending notification to: %s, %s" % (profile.id, profile.uuid)
                    print e

def setProfileLocation(profile):
    dbName = profile.getDBName()
    connection = Connection(
        host=random.choice(getattr(settings, "MONGODB_HOST", None)),
        port=getattr(settings, "MONGODB_PORT", None),
        readPreference='nearest'
    )
    collection = connection[dbName]["funf"]
    
    location = collection.find_one({"key": "edu.mit.media.funf.probe.builtin.LocationProbe"})
    try:
        lat = location["value"]["mlatitude"]
        lng = location["value"]["mlongitude"]
        profile.lat = int(lat*1000000.0)
        profile.lng = int(lng*1000000.0)
        profile.location_last_set = datetime.now()
        profile.save()
    except:
        pass
    connection.close()

@task()
def emojiLocations():
    SIX_HOURS_AGO = datetime.now() - timedelta(hours=6)
    emojis = Emoji.objects.filter(lat__isnull=True).order_by('-created')
    for emoji in emojis:
        setProfileLocation(emoji.profile)
        if emoji.profile.lat:
            emoji.lat = emoji.profile.lat
            emoji.lng = emoji.profile.lng
            emoji.save()

@task()
def profileLocations():
    SIX_HOURS_AGO = datetime.now() - timedelta(hours=6)
    profiles = Profile.objects.filter(location_last_set__lt=SIX_HOURS_AGO).order_by('location_last_set')
    for profile in profiles:
        profileLocation.delay(profile.pk)
        
@task()
def profileLocation(pk):
    profile = Profile.objects.get(pk=pk)
    setProfileLocation(profile)
    
@task()
def setInfluenceScores():
    profiles = Profile.objects.filter(referral__isnull=False).order_by('-created')
    for profile in profiles:
        setInfluenceScore.delay(profile.referral.pk)
        
@task()
def setInfluenceScore(pk):
    profile = Profile.objects.get(pk=pk)
    score = 0
    for child in profile.profile_set.all():
        score += int(child.score * .333) + 10
    if profile.score != score:
        profile.score = score
        profile.save()
    
@task()
def cleanExpiredReferrals():
    ONE_MONTH_AGO = datetime.now() - timedelta(days=30)
    IPReferral.objects.filter(created__lt=ONE_MONTH_AGO).delete()
    
@task()
def checkForProfileReferral(pk, ip):
    profile = Profile.objects.get(pk=pk)
    if not profile.referral:
        ref = IPReferral.objects.filter(created__lt=profile.created, ip=ip).order_by('-created')
        if len(ref) > 0:
            profile.referral = ref[0].profile
            profile.save()