from django.shortcuts import render_to_response
from django.template import RequestContext
import pdb
from openpds.visualization.internal import getInternalDataStore
from openpds.core.models import Profile, Baseline, FB_Connection, Emoji, emoji_choices, QuestionInstance, QuestionType, FirebaseToken, IPReferral
import facebook
import json, datetime, time, re, math, pytz
from django.http import HttpResponse, Http404, HttpResponseRedirect, HttpResponseForbidden
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from calendar import monthrange
from openpds.questions.tasks import checkForProfileReferral
from django.views.decorators.cache import cache_page
import logging
from django.utils import timezone

from django.conf import settings
import requests

@cache_page(60 * 60 * 6)
def flumojiPreSplash(request):
    datastore_owner_uuid = request.GET["datastore_owner"]
    access_token = request.GET["bearer_token"]
    return render_to_response("visualization/flumoji_presplash.html", {
        'uuid': datastore_owner_uuid,
        'access_token': access_token,
    }, context_instance=RequestContext(request))
    

def flumojiSplash(request):
    #return flumojiFriends(request)
    datastore_owner_uuid = request.GET["datastore_owner"]
    access_token = request.GET["bearer_token"]
    profile, ds_owner_created = Profile.objects.get_or_create(uuid = datastore_owner_uuid)
    if not profile.referral:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[-1]
        else:
            ip = request.META.get('REMOTE_ADDR')
        #checkForProfileReferral.delay(profile.pk, ip)
    
    thirty_minutes_ago  = datetime.datetime.utcnow() - datetime.timedelta(minutes=30)
    try:
        latestEmoji = profile.agg_latest_emoji if profile.agg_latest_emoji_update > thirty_minutes_ago else None
    except:
        try:
            latestEmoji = profile.agg_latest_emoji if profile.agg_latest_emoji_update > pytz.utc.localize(thirty_minutes_ago) else None
        except:
            latestEmoji = None
            
    dialog = not bool(latestEmoji) and profile.created > (timezone.now() - datetime.timedelta(hours=1))
    
    return render_to_response("visualization/flumoji_splash.html", {
        'uuid': datastore_owner_uuid,
        'access_token': access_token,
        'latestEmoji': latestEmoji,
        'dialog': dialog,
    }, context_instance=RequestContext(request))

def flumojiFriends(request):
    datastore_owner_uuid = request.GET["datastore_owner"]
    bearer_token = request.GET["bearer_token"]
    profile, ds_owner_created = Profile.objects.get_or_create(uuid = datastore_owner_uuid)
    internalDataStore = getInternalDataStore(profile, "MGH smartCATCH", "Social Health Tracker", "")

    try:
        avgs = internalDataStore.getAnswer("test")[0]['value']
        print str(avgs)
    except:
        internalDataStore.saveAnswer("test", { 'test': 'it is working'})
    
    friends_by_emoji = {}
    if profile.fbid:
        for choice in emoji_choices:
            friends_by_emoji[choice[0]] = []
        fb_friends = Profile.objects.filter(profile2__profile1=profile, profile2__profile2_sharing=True) | Profile.objects.filter(profile1__profile2=profile, profile1__profile1_sharing=True)
        fb_friends = fb_friends.exclude(pk=profile.pk).order_by('-agg_latest_emoji_update')
        
        if fb_friends.count() == 0:
            friends_by_emoji = None
        else:
            for friend in fb_friends:
                friends_by_emoji[friend.agg_latest_emoji].append(friend)
    
    return render_to_response("visualization/flumoji_friends.html", {
        'uuid': datastore_owner_uuid,
        'connected_to_fb': bool(profile.fbid),
        'friends_by_emoji': friends_by_emoji,
        'ds': datastore_owner_uuid,
        'token': bearer_token,
        'profile': profile,
    }, context_instance=RequestContext(request))

def flumojiFacebook(request):
    if request.method == "POST" and 'access_token' in request.POST and 'ds' in request.POST:
        datastore_owner_uuid = request.POST['ds']
        profile, ds_owner_created = Profile.objects.get_or_create(uuid = datastore_owner_uuid)
        
        token = request.POST['access_token']
        print token
        graph = facebook.GraphAPI(access_token=token, version="2.2")
        
        me = graph.get_object(id='me')
        args = {"type": "large", }
        pic = graph.get_object(id='me/picture', **args)
        meid = me['id']
        profile.fbid = meid
        profile.fbname = me['name']
        profile.fbpic = pic['url']
        profile.save()
        
        
        
        friends = graph.get_connections(id='me', connection_name='friends')
        data = friends['data']
        for d in data:
            friendid = d['id']
            friend_profile = Profile.objects.filter(fbid=friendid)
            if len(friend_profile) > 0:
                profile1 = profile if friendid > meid else friend_profile[0]
                profile2 = profile if friendid < meid else friend_profile[0]
                FB_Connection.objects.get_or_create(profile1=profile1, profile2=profile2)
                
    return HttpResponse(json.dumps({"success": True }), content_type="application/json")
        
def flumojiSendEmoji(request):
    if request.method == "POST" and 'access_token' in request.POST and 'ds' in request.POST and 'emoji' in request.POST:
        datastore_owner_uuid = request.POST['ds']
        emoji = request.POST['emoji']
        profile, ds_owner_created = Profile.objects.get_or_create(uuid = datastore_owner_uuid)
        token = request.POST['access_token']
        
        five_minutes_ago  = pytz.utc.localize(datetime.datetime.utcnow() - datetime.timedelta(seconds=300))
        Emoji.objects.filter(profile=profile, created__gt=five_minutes_ago).delete()
        new_emoji = Emoji(profile=profile, emoji=emoji)
        new_emoji.save()
        
        profile.agg_latest_emoji = new_emoji.emoji
        profile.agg_latest_emoji_update = new_emoji.created
        profile.save()
        
        if Baseline.objects.filter(profile=profile).count() == 0:
            try:
                ip = get_client_ip_base(request.META.get('HTTP_X_FORWARDED_FOR'), request.META.get('REMOTE_ADDR'))
                baseline = Baseline.objects.filter(profile__isnull=True, ip=ip).order_by('-pk')[0]
                baseline.profile = profile
                baseline.save()
            except:
                pass
    return HttpResponse(json.dumps({"success": True }), content_type="application/json")
    
def flumojiQuestions(request):
    token = request.GET['bearer_token']
    datastore_owner_uuid = request.GET["datastore_owner"]
    datastore_owner, ds_owner_created = Profile.objects.get_or_create(uuid = datastore_owner_uuid)
    #TODO need to check that the token is in scope
    
    refresh = False
    for key in request.GET:
        if re.search('^q_', key) != None:
            pk = int(re.sub(r'^q_', '', key))
            value = request.GET[key]
            q = QuestionInstance.objects.filter(pk=pk)
            if value != "" and q.count() > 0 and q[0].expired == False:
                q = q[0]
                q.answer = int(float(value))
                q.save()
                refresh = True
    if refresh:
        return HttpResponseRedirect(reverse(flumojiQuestions) +"?bearer_token="+token+"&datastore_owner="+datastore_owner_uuid)
        
    questions = QuestionInstance.objects.filter(expired=False, answer__isnull=True, profile=datastore_owner).order_by("-datetime")
    questionsRemainingList = []
    for q in questions:
        expiry = q.datetime + datetime.timedelta(minutes=q.question_type.expiry)
        if expiry.replace(tzinfo=None) < datetime.datetime.now():
            q.expired = True
            q.save()
        else:
            questionsRemainingList.append((q, q.question_type.optionList()))

    try:
        #weeks = internalDataStore.getAnswerList("activityScoreHistory")[0]['value'][0]["time"]
        weeks = time.mktime(datastore_owner.created.timetuple())
        weeks = math.ceil((time.time() - weeks)/(60 * 60 * 24 * 7))
    except:
        weeks = 1
        
    #if len(questionsRemainingList) == 0:
    #    return HttpResponseRedirect(reverse(flumojiSplash) +"?bearer_token="+token+"&datastore_owner="+datastore_owner_uuid)
    template = "visualization/flumoji_questions.html"
    
    return render_to_response(template, {
        "questions": questionsRemainingList,
        "bearer_token": token,
        "datastore_owner": datastore_owner_uuid,
        'weeksSinceStart': weeks,
    }, context_instance=RequestContext(request))

@cache_page(60 * 60 * 6)
def flumojiMedia(request):
    return render_to_response("visualization/flumoji_media.html", {
    }, context_instance=RequestContext(request))

def get_client_ip_base(x_forwarded_for, remote_addr):
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = remote_addr
    return ip

@cache_page(60 * 60 * 12)
def flumojiConsent(request):
    if request.method == "POST" and request.POST.__contains__('q1') and request.POST.__contains__('q2') and request.POST.__contains__('q3'):
        ip = get_client_ip_base(request.META.get('HTTP_X_FORWARDED_FOR'), request.META.get('REMOTE_ADDR'))
        q1 = request.POST['q1'] == 'true'
        q2 = request.POST['q2'] == 'true'
        q3 = request.POST['q3'] == 'true'
        Baseline.objects.create(ip=ip, q1=q1, q2=q2, q3=q3)
        return HttpResponseRedirect("/takemeback")
    return render_to_response("visualization/flumoji_consent.html", {
    }, context_instance=RequestContext(request))

@cache_page(60 * 60 * 6)
def flumojiPrivacy(request):
    return render_to_response("visualization/flumoji_privacy.html", {
    }, context_instance=RequestContext(request))
    
def flumojiSharingPrefs(request):
    datastore_owner_uuid = request.GET["datastore_owner"]
    bearer_token = request.GET["bearer_token"]
    profile, ds_owner_created = Profile.objects.get_or_create(uuid = datastore_owner_uuid)
    internalDataStore = getInternalDataStore(profile, "MGH smartCATCH", "Social Health Tracker", "")

    fb_conns1 = FB_Connection.objects.filter(profile2=profile).exclude(profile1=profile)
    fb_conns2 = FB_Connection.objects.filter(profile1=profile).exclude(profile2=profile)
        
    return render_to_response("visualization/flumoji_sharing_prefs.html", {
        'fb_conns1': fb_conns1,
        'fb_conns2': fb_conns2,
        'ds': datastore_owner_uuid,
        'token': bearer_token,
    }, context_instance=RequestContext(request))
    
def flumojiChangeSharingPref(request):
    if request.method == "POST" and 'conn' in request.POST and 'ds' in request.POST and 'on' in request.POST:
        datastore_owner_uuid = request.POST['ds']
        profile, ds_owner_created = Profile.objects.get_or_create(uuid = datastore_owner_uuid)
        
        conn_pk = request.POST['conn']
        on = (request.POST['on'] == "true")
        print on
        
        fb_conn = get_object_or_404(FB_Connection, pk=conn_pk)
        if fb_conn.profile1 == profile:
            fb_conn.profile1_sharing = on
        elif fb_conn.profile2 == profile:
            fb_conn.profile2_sharing = on
        fb_conn.save()
        
    return HttpResponse(json.dumps({"success": True }), content_type="application/json")
    
def flumojiHistory(request):
    #return flumojiFriends(request)
    datastore_owner_uuid = request.GET["datastore_owner"]
    access_token = request.GET["bearer_token"]
    profile, ds_owner_created = Profile.objects.get_or_create(uuid = datastore_owner_uuid)
    
    dates = []
    currentMonth = None
    
    emojis = Emoji.objects.filter(profile=profile).order_by("-created")
    for emoji in emojis:
        month = emoji.created.month
        year = emoji.created.year
        date = emoji.created.day
        if not currentMonth or currentMonth["year"] != year or currentMonth["month"] != month:
            startDay, monthLength = monthrange(year, month)
            currentMonth = {"month": month,
                            "year": year,
                            "startDay": [None] * ((startDay+1)%7),
                            "emojis": [None] * monthLength
                            }
            dates.insert(0, currentMonth)
        if not currentMonth["emojis"][date - 1]: #this line uses only the last emoji a user chose for that day
            currentMonth["emojis"][date - 1] = emoji.emoji
    frequencyEmoji = {}
    for emoji in emojis:
        if emoji.created.month != datetime.datetime.now().month:
            break
        if emoji.emoji not in frequencyEmoji:
            frequencyEmoji[emoji.emoji] = 1
        else:
            frequencyEmoji[emoji.emoji] += 1
    mostFrequent = "h"
    frequency = 0
    for e, f in frequencyEmoji.iteritems():
        if f > frequency:
            mostFrequent = e
            frequency = f

    dialog = profile.created > (timezone.now() - datetime.timedelta(hours=2))
    
    return render_to_response("visualization/flumoji_history.html", {
        'uuid': datastore_owner_uuid,
        'access_token': access_token,
        'dates': dates,
        'mostFrequent': mostFrequent,
        'dialog':  dialog,
    }, context_instance=RequestContext(request))
    
def flumojiSplashRedirect(request):
    datastore_owner_uuid = request.GET["datastore_owner"]
    access_token = request.GET["bearer_token"]
    profile, ds_owner_created = Profile.objects.get_or_create(uuid = datastore_owner_uuid)
    if profile.created.month == datetime.datetime.now().month:
        return HttpResponseRedirect(reverse(flumojiInfluence) + "?datastore_owner=%s&bearer_token=%s" % (datastore_owner_uuid, access_token))
    elif profile.fbid:
        return HttpResponseRedirect(reverse(flumojiFriends) + "?datastore_owner=%s&bearer_token=%s" % (datastore_owner_uuid, access_token))
    else:
        return HttpResponseRedirect(reverse(flumojiInfluence) + "?datastore_owner=%s&bearer_token=%s" % (datastore_owner_uuid, access_token))
        #return HttpResponseRedirect(reverse(flumojiHistory) + "?datastore_owner=%s&bearer_token=%s" % (datastore_owner_uuid, access_token))
    def __unicode__(self):
        return self.uuid
    
def setFirebaseToken(request):
    if request.method == 'POST' and request.POST.__contains__('uuid') and request.POST.__contains__('token'):
        token = request.POST['token']
        uuid = request.POST['uuid']
        profile = get_object_or_404(Profile, uuid=uuid)
        ftoken = FirebaseToken.objects.filter(profile=profile)
        if len(ftoken) == 0:
            ftoken = FirebaseToken(profile=profile, token=token)
            ftoken.save()
        elif ftoken[0].token != token:
            ftoken[0].token = token
            ftoken[0].save()
    return HttpResponse()
    
def flumojiInfluence(request):
    datastore_owner_uuid = request.GET["datastore_owner"]
    access_token = request.GET["bearer_token"]
    profile, ds_owner_created = Profile.objects.get_or_create(uuid = datastore_owner_uuid)
    topInfluencers = Profile.objects.filter(fbname__isnull=False).order_by('-score')[0:5]

    dialog = profile.created > (timezone.now() - datetime.timedelta(hours=2))
    return render_to_response("visualization/flumoji_influence.html", {
        'uuid': datastore_owner_uuid,
        'access_token': access_token,
        'profile': profile,
        'topInfluencers': topInfluencers,
        'dialog': dialog,
    }, context_instance=RequestContext(request))
    
def referral(request, pk):
    try:
        profile = Profile.objects.get(pk=pk)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[-1]
        else:
            ip = request.META.get('REMOTE_ADDR')
        ref = IPReferral(profile=profile, ip=ip)
        ref.save()
    except:
        pass
    
    return HttpResponseRedirect('https://play.google.com/store/apps/details?id=edu.mit.media.flumoji')

    