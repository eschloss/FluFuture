from django.conf.urls import patterns, include, url
from django.conf import settings
from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template
from openpds.meetup.views import meetup_home

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('openpds.visualization.stats',
    (r'^dupEmojis$', 'dupEmojis'),
    (r'^getLength$', 'getLength'),
    (r'^randEmojis$', 'randEmojis'),
    (r'^fluQuestionSet$', 'fluQuestionSet'),
)
