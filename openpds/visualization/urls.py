from django.conf.urls import patterns, include, url
from django.conf import settings
from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template
from openpds.meetup.views import meetup_home

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('openpds.visualization.views',
    (r'^socialHealthRadial', direct_to_template, { 'template' : 'visualization/socialHealthRadial.html' }),
    (r'^gfsa', direct_to_template, { 'template' : 'visualization/gfsa.html' }),
    (r'^activity', direct_to_template, { 'template' : 'visualization/activity.html' }),
    (r'^social', direct_to_template, { 'template' : 'visualization/social.html' }),
    (r'^focus', direct_to_template, { 'template' : 'visualization/focus.html' }),
    (r'^meetup_home', meetup_home),
    (r'^probe_counts', direct_to_template, { 'template': 'visualization/probeCounts.html'}),
    (r"^places", direct_to_template, { "template" : "visualization/locationMap.html" }),
    (r'^mitfit/userlocation$', direct_to_template, { 'template' : 'visualization/mitfit_user_location.html' }),
    (r'^mitfit/usertime$', direct_to_template, { 'template' : 'visualization/mitfit_user_time.html' }),
    (r'^mitfit/recos$', direct_to_template, { 'template' : 'visualization/mitfit_recos.html' }),
    (r'^hotspots$', direct_to_template, { 'template' : 'visualization/hotspots.html' }),
    
    (r'^flumoji/presplash$', 'flumojiPreSplash'),
    (r'^flumoji/splash$', 'flumojiSplash'),
    (r'^flumoji/splashRedirect$', 'flumojiSplashRedirect'),
    (r'^flumoji/history$', 'flumojiHistory'),
    (r'^flumoji/friends$', 'flumojiFriends'),
    (r'^flumoji/facebook$', 'flumojiFacebook'),
    (r'^flumoji/sendEmoji$', 'flumojiSendEmoji'),
    (r'^flumoji/questions$', 'flumojiQuestions'),
    (r'^flumoji/media$', 'flumojiMedia'),
    (r'^flumoji/consent$', 'flumojiConsent'),
    (r'^consent$', 'flumojiConsent'),
    (r'^flumoji/sharingPreferences$', 'flumojiSharingPrefs'),
    (r'^flumoji/changeSharingPreference$', 'flumojiChangeSharingPref'),
    (r'^flumoji/firebase$', 'setFirebaseToken'),
    (r'^flumoji/influence$', 'flumojiInfluence'),
    (r'^privacy$', 'flumojiPrivacy'),
)
