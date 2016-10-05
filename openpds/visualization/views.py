from django.shortcuts import render_to_response
from django.template import RequestContext
import pdb
from openpds.visualization.internal import getInternalDataStore
from openpds.core.models import Profile, FB_Connection
import facebook
import json
from django.http import HttpResponse, Http404, HttpResponseRedirect, HttpResponseForbidden

def flumojiSplash(request):
    return flumojiFriends(request)
    return render_to_response("visualization/flumoji_splash.html", {
    }, context_instance=RequestContext(request))

def flumojiFriends(request):
    datastore_owner_uuid = request.GET["datastore_owner"]
    profile, ds_owner_created = Profile.objects.get_or_create(uuid = datastore_owner_uuid)
    internalDataStore = getInternalDataStore(profile, "MGH smartCATCH", "Social Health Tracker", "")

    try:
        avgs = internalDataStore.getAnswer("test")[0]['value']
        print str(avgs)
    except:
        internalDataStore.saveAnswer("test", { 'test': 'it is working'})
    
    return render_to_response("visualization/flumoji_friends.html", {
        'uuid': datastore_owner_uuid,
    }, context_instance=RequestContext(request))

def flumojiFacebook(request):
    if request.method == "POST" and 'access_token' in request.POST and 'ds' in request.POST:
        datastore_owner_uuid = request.POST['ds']
        profile, ds_owner_created = Profile.objects.get_or_create(uuid = datastore_owner_uuid)
        
        token = request.POST['access_token']
        graph = facebook.GraphAPI(access_token=token, version="2.2")
        
        me = graph.get_object(id='me')
        pic = graph.get_object(id='me/picture')
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
        