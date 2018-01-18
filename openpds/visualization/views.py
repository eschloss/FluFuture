from django.shortcuts import render_to_response
from django.template import RequestContext
import pdb
from openpds.visualization.internal import getInternalDataStore
from openpds.core.models import Profile, IphoneDummy, Baseline, FB_Connection, Emoji, emoji_choices, QuestionInstance, QuestionType, FirebaseToken, IPReferral
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
import numpy

from django.conf import settings
import requests

#@cache_page(60 * 60 * 6)
def flumojiPreSplash(request):
    #return flumojiSplash(request)
    #return HttpResponseRedirect(reverse(flumojiSplash) +"?bearer_token="+token+"&datastore_owner="+datastore_owner_uuid)
    
    now = datetime.datetime.utcnow()
    datastore_owner_uuid = request.GET["datastore_owner"]
    access_token = request.GET["bearer_token"]
    profile, ds_owner_created = Profile.objects.get_or_create(uuid = datastore_owner_uuid)
    return render_to_response("visualization/flumoji_presplash.html", {
        'uuid': datastore_owner_uuid,
        'access_token': access_token,
        'days': (now.replace(tzinfo=None) - profile.created.replace(tzinfo=None)).days,
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
    return HttpResponseRedirect("/takemeback")
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
    
    now = datetime.datetime.now()
    emojis = Emoji.objects.filter(profile=profile, created__year=now.year, created__month=now.month).order_by("-created")
    # the following line is for showing more than one month
    #emojis = Emoji.objects.filter(profile=profile).order_by("-created")
    for emoji in emojis:
        created = emoji.created - datetime.timedelta(hours=4)
        month = created.month
        year = created.year
        date = created.day
        # the following line is for showing more than one month
        #if not currentMonth or currentMonth["year"] != year or currentMonth["month"] != month:
        if not currentMonth:
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
        created = created - datetime.timedelta(hours=4)
        if created.month != datetime.datetime.now().month: 
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
    
    if profile.activity_this_week >= 75:
        activity_this_week = 'green'
    elif profile.activity_this_week > 25:
        activity_this_week = 'yellow'
    else:
        activity_this_week = 'red'
    if profile.social_this_week >= 75:
        social_this_week = 'green'
    elif profile.social_this_week > 25:
        social_this_week = 'yellow'
    else:
        social_this_week = 'red'
        
    return render_to_response("visualization/flumoji_history.html", {
        'uuid': datastore_owner_uuid,
        'access_token': access_token,
        'dates': dates,
        'mostFrequent': mostFrequent,
        'dialog':  dialog,
        'activity': activity_this_week,
        'social': social_this_week,
    }, context_instance=RequestContext(request))
    
def flumojiSplashRedirect(request):
    datastore_owner_uuid = request.GET["datastore_owner"]
    access_token = request.GET["bearer_token"]
    profile, ds_owner_created = Profile.objects.get_or_create(uuid = datastore_owner_uuid)
    
    if QuestionInstance.objects.filter(profile=profile, expired=False, answer__isnull=True).count() > 0:
        return HttpResponseRedirect(reverse(flumojiQuestions) + "?datastore_owner=%s&bearer_token=%s" % (datastore_owner_uuid, access_token))
    
    return HttpResponseRedirect(reverse(flumojiHistory) + "?datastore_owner=%s&bearer_token=%s" % (datastore_owner_uuid, access_token))
    
    """
    if profile.created.month == datetime.datetime.now().month:
        return HttpResponseRedirect(reverse(flumojiInfluence) + "?datastore_owner=%s&bearer_token=%s" % (datastore_owner_uuid, access_token))
    elif profile.fbid:
        return HttpResponseRedirect(reverse(flumojiFriends) + "?datastore_owner=%s&bearer_token=%s" % (datastore_owner_uuid, access_token))
    else:
        return HttpResponseRedirect(reverse(flumojiInfluence) + "?datastore_owner=%s&bearer_token=%s" % (datastore_owner_uuid, access_token))
        #return HttpResponseRedirect(reverse(flumojiHistory) + "?datastore_owner=%s&bearer_token=%s" % (datastore_owner_uuid, access_token))
    """
    def __unicode__(self):
        return self.uuid
    
def setFirebaseToken(request):
    if request.method == 'POST' and request.POST.__contains__('uuid') and request.POST.__contains__('token'):
        token = request.POST['token']
        uuid = request.POST['uuid']
        profile = get_object_or_404(Profile, uuid=uuid)
        ftokens = FirebaseToken.objects.filter(profile=profile, old=False)
        same_token = ftokens.filter(token=token)
        if len(same_token) == 0:
            ftokens.update(old=True)
            ftoken = FirebaseToken(profile=profile, token=token, old=False)
            ftoken.save()
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

def appDownload(request):
    pass

def collectVists(request):
    if request.method == 'POST':
        POST = request.POST
        if POST.__contains__('email') and POST.__contains__('visits'):
            email = request.POST['email']
            visits = request.POST['visits']
            #iphone = IphoneDummy.objects.filter(email=email).order_by('-pk')
            #if len(iphone) == 0:
            iphone = IphoneDummy(email=email, visits=visits)
            #else:
            #    iphone = iphone[0]
            #    iphone.visits = visits
            if POST.__contains__('hospital'):
                hospital = request.POST['hospital']
                try:
                    if int(hospital) in [0,1,2,3,4]:
                        iphone.hospital = hospital
                except:
                    pass
            iphone.save()
            return HttpResponse(json.dumps({"success": True }), content_type="application/json")
    return HttpResponse(json.dumps({"success": False }), content_type="application/json")
    
def timestampToStart(ts):
    return datetime.datetime.combine(datetime.datetime.fromtimestamp(ts), datetime.time.min)
def timestampToEnd(ts):
    return datetime.datetime.combine(datetime.datetime.fromtimestamp(ts), datetime.time.max)

def liversmart_graph(request, interval, datastore_owner_uuid):
    return liversmart_graph2(request, interval, None, None, datastore_owner_uuid)
    
def liversmart_graph2(request, interval, start_date, end_date, datastore_owner_uuid):
    profile, ds_owner_created = Profile.objects.get_or_create(uuid = datastore_owner_uuid)

    ids = getInternalDataStore(profile, "Living Lab", "Social Health Tracker", "")
    
    if start_date and end_date:
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        print start_date
        print end_date
    
    rabh = None
    rsbh = None

    chart_emojis = []
    emojis = Emoji.objects.filter(profile__uuid=datastore_owner_uuid)

    if interval == "social":
        rsbh2 = ids.getAnswerList("RecentSocialByHour")[0]['value']
        rsbh = []
        for r in rsbh2:
            ts = timestampToStart(r['start'])
            if ts > profile.created.replace(tzinfo=None) and ((not start_date or not end_date) or (ts > start_date and ts < end_date)):
                rsbh.append(r)
                e = emojis.filter(created__day=ts.day, created__month=ts.month, created__year=ts.year)
                if e.count() > 0:
                    chart_emojis.append(e[0])
                else:
                    chart_emojis.append("")
    elif interval == "activity":
        rabh2 = ids.getAnswerList("RecentActivityByHour")[0]['value']
        rabh = []
        for r in rabh2:
            ts = timestampToStart(r['start'])
            if (not start_date or not end_date) or (ts > start_date and ts < end_date):
                rabh.append(r)
                e = emojis.filter(created__day=ts.day, created__month=ts.month, created__year=ts.year)
                if e.count() > 0:
                    chart_emojis.append(e[0])
                else:
                    chart_emojis.append("")
    elif interval == "activity2":
        for r in rabh:
            chart_emojis.append("")
    else:
        pass
    
            
    return render_to_response("visualization/liversmart_graph.html", {
        'uuid': datastore_owner_uuid,
        'interval': interval,
        'profile': profile,
        'ids': ids,
        'rabh': rabh,
        'rsbh': rsbh,
        'emojis': chart_emojis,
    }, context_instance=RequestContext(request))

def liversmart_sync(request):
    from openpds.questions.socialhealth_tasks import recentSocialHealthScores
    recentSocialHealthScores(isTask=False)
    return HttpResponse("success")