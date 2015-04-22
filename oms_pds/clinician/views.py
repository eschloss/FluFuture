from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from rdflib import Graph
from SPARQLWrapper import SPARQLWrapper, JSON
import rdflib
from oms_pds.pds.internal import getInternalDataStore
import pdb, datetime, re, time, math
from oms_pds.pds.models import Profile, QuestionInstance, QuestionType
from django.core.urlresolvers import reverse
from django.db.models import Avg, StdDev
import json
import random


####
# FOR TESTING
####
def breakdown_history_test(scores):
    scores = [{'score': random.random() * 100} for r in xrange(100)]
    return breakdown_history(scores, accessor='score')
###############


def breakdown_history(scores, accessor=None):
    """breaks down the users' scores to individual percentages for
    "good", "medium", and "bad".

    returns a dict of the form:
    {'good': <percent_good>
    'medium': <percent_medium>
    'bad': <percent_bad>}
    """
    if accessor:
        scores = [s[accessor] for s in scores]
    percents = {'good': [s for s in scores if s >= 70],
                'medium': [s for s in scores if s >= 50 and s < 70],
                'bad': [s for s in scores if s < 50]}

    return [{'status': k,
             'score': len(v) / float(len(scores))} for k, v in percents.items()]

def get_participant_scores(p):
    """Get a summary object of this participants' scores of the form:
    {<aspect>: [{'timestamp': <timestamp>, 'score': <score>}], ...}
    """
    goal_map = {'f': 'Foot Care',
                's': 'Smoking',
                'e': 'Eating Healthy',
                't': 'Stress Level'}

    ids = getInternalDataStore(p, "MGH smartCATCH", "Social Health Tracker", "")

    sleepScoreHistory = ids.getAnswerList("sleepScoreHistory")[0]['value']
    glucoseScoreHistory = ids.getAnswerList("glucoseScoreHistory")[0]['value']
    medsScoreHistory = ids.getAnswerList("medsScoreHistory")[0]['value']
    activityScoreHistory = ids.getAnswerList("activityScoreHistory")[0]['value']
    socialScoreHistory = ids.getAnswerList("socialScoreHistory")[0]['value']
    focusScoreHistory = ids.getAnswerList("focusScoreHistory")[0]['value']
    goalScoreHistory = ids.getAnswerList("goalScoreHistory")[0]['value']

    obj = {'Sleep': sleepScoreHistory,
           'Glucose': glucoseScoreHistory,
           'Medications': medsScoreHistory,
           'Activity': activityScoreHistory,
           'Social': socialScoreHistory,
           'Focus': focusScoreHistory,
           goal_map[p.goal].replace(' ', '-'): goalScoreHistory}
    return obj


def get_participant_object(p):
    """ Get object corresponding to this participant of the form:

    {<aspect>: {'good': %,
                'bad': %,
                'medium': %'}
    "uid": <uid> }
    """
    # dict of {key: {'good': <%> 'medium': <%>, 'bad': <%>}, ...}
    obj = {k: breakdown_history_test(v) for k, v in p['scores'].items()}
    obj['uid'] = p['uid']
    return obj


def aggregate_scores(all_participant_scores):
    """Get an aggregate time-series object of all participants' scores of the form:
    [{'date': <date>, 'value': <%>, 'key': <{'good', 'bad', 'medium'}>}]
    """
    all_scores = {}
    for p in all_participant_scores:
        uid = p['uid']
        scores = p['scores']
        scores = [v for k, v in scores.items()]
        scores = [item for sublist in scores for item in sublist] #flatten
        for obj in scores:
            time = datetime.datetime.fromtimestamp(obj['time'])
            time = time.strftime('%x')
            score = obj['score']
            if time in all_scores.keys():
                all_scores[time].append(score)
            else:
                all_scores[time] = [score]

    obj = []
    for time, scores in all_scores.items():
        for s in breakdown_history(scores):
            obj.append({'value': s['score'],
                        'date': time,
                        'key': s['status']})
    return sorted(obj, key=lambda s: s['date'])


def uid_name_map():
    """ Returns a map of users' UID's to temporary patient names:
    {<uid>: "Patient X"}
    where X is an integer count, starting from 1
    """
    allParticipants = Profile.objects.filter(study_status__in=['i', 'c'])
    # map of UID -> "Patient X"
    uid_name_map = {}
    uids = [p.uuid for p in allParticipants]
    for n, uid in enumerate(uids):
        uid_name_map[uid] = "Patient {}".format(n + 1)
    return uid_name_map


def groupOverview(request):
    """renders the group overview page.
    """
    # patient_status = [request.GET['patient_status']]
    # if patient_status == ['b']:
    #     patient_status = ['i', 'c']

    allParticipants = Profile.objects.filter(study_status__in=['i', 'c'])

    data = [{'uid': p.uuid, 'scores': get_participant_scores(p)} for p in allParticipants]

    participant_data = []
    for p in data:
        participant_data.append(get_participant_object(p))
        # try:
        # except:
        #     continue

    # for n in xrange(10):
    #     obj2 = participant_data[0].copy()
    #     obj2['uid'] = "test-{}".format(n)
    #     participant_data.append(obj2)

    all_scores = aggregate_scores(data)

    return render_to_response("clinician/group_overview.html",
                              {'num_participants': len(participant_data),
                               'participant_data': json.dumps(participant_data),
                               'aggregate_scores': json.dumps(all_scores),
                               'uid_name_map': uid_name_map(),
                               'uid_name_map_json': json.dumps(uid_name_map())
                           },
                              context_instance=RequestContext(request))


def patientInfo(request, uid=None):
    """ Renders a patient info page for the patient with uid <uid>.
    """

    profile, created = Profile.objects.get_or_create(uuid=uid)

    internalDataStore = getInternalDataStore(profile, "MGH smartCATCH", "Social Health Tracker", "")

    try:
        avgs = internalDataStore.getAnswer("socialhealthavgs")[0]['value']
        socialhealth = internalDataStore.getAnswer("socialhealth")[0]['value']
        surveyscores = internalDataStore.getAnswer("surveyscores")[0]['value']
        sleepScoreHistory = internalDataStore.getAnswerList("sleepScoreHistory")[0]['value']
        glucoseScoreHistory = internalDataStore.getAnswerList("glucoseScoreHistory")[0]['value']
        medsScoreHistory = internalDataStore.getAnswerList("medsScoreHistory")[0]['value']
        activityScoreHistory = internalDataStore.getAnswerList("activityScoreHistory")[0]['value']
        socialScoreHistory = internalDataStore.getAnswerList("socialScoreHistory")[0]['value']
        focusScoreHistory = internalDataStore.getAnswerList("focusScoreHistory")[0]['value']
        goalScoreHistory = internalDataStore.getAnswerList("goalScoreHistory")[0]['value']
        activityScoreGroupHistory = internalDataStore.getAnswerList("activityScoreGroupHistory")[0]['value']
        socialScoreGroupHistory = internalDataStore.getAnswerList("socialScoreGroupHistory")[0]['value']
        focusScoreGroupHistory = internalDataStore.getAnswerList("focusScoreGroupHistory")[0]['value']
        sleepScoreGroupHistory = internalDataStore.getAnswerList("sleepScoreGroupHistory")[0]['value']
        glucoseScoreGroupHistory = internalDataStore.getAnswerList("glucoseScoreGroupHistory")[0]['value']
        medsScoreGroupHistory = internalDataStore.getAnswerList("medsScoreGroupHistory")[0]['value']
        goalScoreGroupHistory = internalDataStore.getAnswerList("goalScoreGroupHistory")[0]['value']
    except:
        return HttpResponse("Not enough data collected. Please wait.")

    currentTime = time.time();
    #currentTime = 1425186000

    return render_to_response("clinician/patient_info.html", {
        'uid': uid,
        'uid_name_map': uid_name_map(),
        'uid_name_map_json': json.dumps(uid_name_map()),

        'userHistory': {'sleep': sleepScoreHistory,
                        'glucose': glucoseScoreHistory,
                        'meds': medsScoreHistory,
                        'activity': activityScoreHistory,
                        'social': socialScoreHistory,
                        'focus': focusScoreHistory,
                        'goal': goalScoreHistory
                    },
        'groupHistory': {'sleep': activityScoreGroupHistory,
                         'glucose': glucoseScoreGroupHistory,
                         'meds': medsScoreGroupHistory,
                         'activity': activityScoreGroupHistory,
                         'social': socialScoreGroupHistory,
                         'focus': focusScoreGroupHistory,
                         'goal': goalScoreGroupHistory,

                                },
        'socialhealth': socialhealth,
        'surveyscores': surveyscores,
        'avgActivity': avgs["activity"],
        'avgSocial': avgs["social"],
        'avgFocus': avgs["focus"],
        'avgSleep': avgs["sleep"],
        'avgGlucose': avgs["glucose"],
        'avgMeds': avgs["meds"],
        'avgGoal': avgs["goal"],

        'dayCutoff': currentTime - 24 * 3600,
        'weekCutoff': currentTime - 7 * 24 * 3600,
        'monthCutoff': currentTime - 30 * 24 * 3600,
        'goaltype': profile.goal,
        'control': profile.study_status == 'c',
    }, context_instance=RequestContext(request))
