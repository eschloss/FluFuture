from django.shortcuts import render_to_response
from django.template import RequestContext
import pdb
from oms_pds import getInternalDataStore

def flumojiSplash(request):
    return render_to_response("visualization/flumoji_splash.html", {
    }, context_instance=RequestContext(request))

def flumojiFriends(request):
    datastore_owner_uuid = request.GET["datastore_owner"]
    profile, ds_owner_created = Profile.objects.get_or_create(uuid = datastore_owner_uuid)
    internalDataStore = getInternalDataStore(profile, "MGH smartCATCH", "Social Health Tracker", "")
