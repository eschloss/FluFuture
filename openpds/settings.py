# Django settings for openPDS project.

import os
try:
    BUILD = os.environ['BUILD']
except:
    BUILD = 'DEV'
IS_PRODUCTION_SERVER = (BUILD == 'PRODUCTION')
IS_STAGING_SERVER = (BUILD == 'STAGING')
IS_DEV_SERVER = not IS_STAGING_SERVER and not IS_PRODUCTION_SERVER
DEBUG = not IS_PRODUCTION_SERVER

# Standard Django settings for turning on debug messages
TEMPLATE_DEBUG = DEBUG

# Note: these should be stored in config variables. Leaving them here for now for clarity.
if IS_PRODUCTION_SERVER:
    # Used to specify the registry server to use for authorization
    REGISTRY_SERVER='flumoji-registry-production.herokuapp.com'
    
    # Deprecated: Used to specify the default PDS url for aggregate computation
    DEFAULT_PDS_URL = 'flumoji-pds-production.herokuapp.com'
elif IS_STAGING_SERVER:
    # Used to specify the registry server to use for authorization
    REGISTRY_SERVER='flufuture-registry.herokuapp.com'
    
    # Deprecated: Used to specify the default PDS url for aggregate computation
    DEFAULT_PDS_URL = 'flufuture-openpds.herokuapp.com'
else:
    # Used to specify the registry server to use for authorization
    REGISTRY_SERVER='localhost:8000'
    
    # Deprecated: Used to specify the default PDS url for aggregate computation
    DEFAULT_PDS_URL = 'localhost:8002'
    

# Specifies where files posted to connectors will be placed while inserting into the PDS
if IS_DEV_SERVER:
    SERVER_UPLOAD_DIR="/Users/ericschlossberg/Dropbox/Documents/workspace/gsk/pdsEnv"
else:
    SERVER_UPLOAD_DIR="/tmp"

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

# Standard Django database specification. See Django docs for further information.
if IS_DEV_SERVER:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3', 
            'NAME': 'test.db',      
            'USER': 'default',      
            'PASSWORD': 'default',  
            'HOST': '',      
            'PORT': '',      
        }
    }
else:
    import dj_database_url
    DATABASES = {}
    DATABASES['default'] =  dj_database_url.config()
    DATABASES['default']['CONN_MAX_AGE'] = None
    #PDS_BACKEND =  dj_database_url.config()

# Specifies the backend storage database for personal data
PDS_BACKEND = {
    "ENGINE": 'openpds.backends.mongo',
    "USER": "",
    "PASSWORD": "",
    "HOST": "",
    "PORT": ""
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/New_York'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC_ROOT = os.path.join(PROJECT_ROOT, 'staticfiles')

STATICFILES_STORAGE = 'whitenoise.django.GzipManifestStaticFilesStorage'


# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(os.path.dirname(__file__), 'static'),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'r6ce2%&xce!o!t9$i(#2rxr)=49a_u8@pwiye^ug6f82#5qa!!'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    #'django.middleware.csrf.CsrfViewMiddleware',
    'openpds.django-crossdomainxhr-middleware.XsSharing',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'openpds.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'openpds.wsgi.application'

TEMPLATE_DIRS = (os.path.join(os.path.dirname(__file__), 'templates'),)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.humanize',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'djcelery',
    'openpds.core',
    'openpds.accesscontrol',
    'openpds.questions',
    'kombu.transport.django',
    'openpds.visualization',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)


#import celery_settings

"""
CELERY_IMPORTS = celery_settings.CELERY_IMPORTS
BROKER_URL = celery_settings.BROKER_URL
CELERYBEAT_SCHEDULE = celery_settings.CELERYBEAT_SCHEDULE
"""

import djcelery
djcelery.setup_loader()

CELERYD_MAX_TASKS_PER_CHILD = 150
BROKER_POOL_LIMIT = 3

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

if not IS_DEV_SERVER:
    BROKER_URL = os.environ['RABBITMQ_BIGWIG_TX_URL']


# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
'''
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}
'''
# XXX - figure out where this is going and why we want to use this over the
# framework django provides
import logging
import sys
logger = logging.getLogger('')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stderr)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

#GCM_API_KEY = "AIzaSyBTGmBjzM9_CETLxU3YEbtWIS_OUGWHr0s"
#GCM_API_KEY = "AIzaSyAWLJU1-g9hn2UWiFqLyS9U57BhOwOaVlY"
#GCM_API_KEY = "AIzaSyBK933WZvgHi3bYBbuLbVhhFWth-jFHfGI"
if IS_DEV_SERVER:
    GCM_API_KEY = "AIzaSyDG4sVsp3iLlYoceleXz3jd5Z32O6DgFBk"
else:
    GCM_API_KEY = os.environ["GCM_API_KEY"]


MONGODB_HOST = os.environ['MONGODB_HOST']
MONGODB_PORT = int(os.environ['MONGODB_PORT'])
