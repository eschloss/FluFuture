from django.conf import settings
from django.db import models
import datetime
import json

emoji_choices = (
    ('h', 'positive'),
    ('d','unhappy'),
    ('f', 'sick'),
    ('s', 'happy'),
    ('y', 'sleepy'),
    ('c', 'worried'),
    ('u', 'restless'),
    ('n', 'acutely ill'),
    ('l', 'confused'),
    ('b', 'in pain'),
    
    #the rest we aren't using
    ('r', 'runnynose'),
    ('a','calm'),
    ('e','energized'),
    ('m','motivated'),
    ('t','trouble concentrating'),
    
)

class Profile(models.Model):
    uuid = models.CharField(max_length=36, unique=True, blank = False, null = False, db_index = True)
    fbid = models.BigIntegerField(blank=True, null=True) #TODO. if a user changes his fbid, must delete all connected FB_Connections
    fbpic = models.URLField(blank=True, null=True)
    fbname = models.CharField(max_length=50, blank=True, null=True) 
    created = models.DateTimeField(auto_now_add=True)
    agg_latest_emoji = models.CharField(choices=emoji_choices, max_length=1, default="h")
    agg_latest_emoji_update = models.DateTimeField(default=datetime.datetime.now)
    lat = models.IntegerField(blank=True, null=True)
    lng = models.IntegerField(blank=True, null=True)
    location_last_set = models.DateTimeField(default=datetime.datetime.now) #repurposed. using it now for firebase
    referral = models.ForeignKey('Profile', blank=True, null=True)
    score = models.IntegerField(default=0)
    activity_this_week = models.IntegerField(default=50)
    social_this_week = models.IntegerField(default=50)

    def getDBName(self):
        return "User_" + str(self.uuid).replace("-", "_")
   
    def __unicode__(self):
        return self.uuid
    
class IPReferral(models.Model):
    profile = models.ForeignKey('Profile')
    ip = models.CharField(max_length=39)
    created = models.DateTimeField(auto_now_add=True)
    
class FirebaseToken(models.Model):
    profile = models.ForeignKey('Profile')
    token = models.CharField(max_length=255, default="")
    created = models.DateTimeField(auto_now_add=True)
    old = models.BooleanField(default=False)

    def __unicode__(self):
        return self.profile.uuid
    
class FB_Connection(models.Model):
    profile1 = models.ForeignKey('Profile', related_name="profile1") #this must have the fbid lower than profile2
    profile1_sharing = models.BooleanField(default=True) #is profile 1 sharing with profile 2
    profile2 = models.ForeignKey('Profile', related_name="profile2")
    profile2_sharing = models.BooleanField(default=True) # is profile 2 sharing with profile 1
    
class Emoji(models.Model):
    profile = models.ForeignKey('Profile')
    emoji = models.CharField(choices=emoji_choices, max_length=1)
    created = models.DateTimeField(auto_now_add=True)
    lat = models.IntegerField(blank=True, null=True)
    lng = models.IntegerField(blank=True, null=True)

class Emoji2(models.Model):
    profile = models.ForeignKey('Profile')
    emoji = models.CharField(choices=emoji_choices, max_length=1)
    created = models.DateTimeField()
    lat = models.IntegerField(blank=True, null=True)
    lng = models.IntegerField(blank=True, null=True)

class FluQuestions(models.Model):
    profile = models.ForeignKey('Profile')
    fluThisSeason = models.BooleanField()
    fluLastSeason = models.BooleanField()
    vaccineThisSeason = models.BooleanField()
    
class ProfileStartEnd(models.Model):
    profile = models.ForeignKey('Profile')
    start = models.DateTimeField(blank=True, null=True)
    end = models.DateTimeField(blank=True, null=True)
    days = models.IntegerField(default=0)

class AuditEntry(models.Model):
    '''
    Represents an audit of a request against the PDS
    Given that there will be many entries (one for each request), 
    we are strictly limiting the size of data entered for each row
    The assumption is that script names and symbolic user ids
    will be under 64 characters 
    '''
    datastore_owner = models.ForeignKey(Profile, blank = False, null = False, related_name="auditentry_owner", db_index=True)
    requester = models.ForeignKey(Profile, blank = False, null = False, related_name="auditentry_requester", db_index=True)
    method = models.CharField(max_length=10)
    scopes = models.CharField(max_length=1024) # actually storing csv of valid scopes
    purpose = models.CharField(max_length=64, blank=True, null=True)
    script = models.CharField(max_length=64)
    token = models.CharField(max_length=64)
    system_entity_toggle = models.BooleanField()
    trustwrapper_result = models.CharField(max_length=64)
    timestamp = models.DateTimeField(auto_now_add = True, db_index=True)
    
    def __unicode__(self):
        self.pk

class Notification(models.Model):
    '''
    Represents a notification about a user's data. This can be filled in while constructing answers
    '''
    datastore_owner = models.ForeignKey(Profile, blank = False, null = False, related_name="notification_owner")
    title = models.CharField(max_length = 64, blank = False, null = False)
    content = models.CharField(max_length = 1024, blank = False, null = False)
    type = models.IntegerField(blank = False, null = False)
    timestamp = models.DateTimeField(auto_now_add = True)
    uri = models.URLField(blank = True, null = True)
    
    def __unicode__(self):
        self.pk

class Device(models.Model):

    datastore_owner = models.ForeignKey(Profile, blank=False, null=False, related_name="device_owner", db_index=True)
    gcm_reg_id = models.CharField(max_length=1024, blank=False, null=False)

class QuestionType(models.Model):
    UI_CHOICES = (
        ('s', 'Slider'),
        ('b', 'Binary (Yes/No)'),
        ('m', 'Multiple Choice'),
    )
    
    text = models.TextField() #What was your morning Glucose level?
    ui_type = models.CharField(max_length=1, choices=UI_CHOICES)
    params = models.TextField(default="[]", help_text="this column must be coded in JSON and is specific to the uitype - for YES/NO params=[], for slider params='[ [min, \"label\"], [max, \"label\"] ]' ie '[[ 0, \"worst\"], [10, \"best\"]]', Multiple Choice '[ [0, \"Never\"], [1, \"Some\"], [2, \"All\" ]]'")
    frequency_interval = models.IntegerField(default=1440, blank=True, null=True, help_text="minutes between the next time the question is asked. set as null if the question isn't set on a schedule directly.")
    resend_quantity = models.IntegerField(default=0, help_text="Number of times to resend this question until it's answered.")
    followup_key = models.IntegerField(blank=True, null=True, help_text="If this question result in a followup question, select the answer that results in a follow up. If not, or if any answer creates a follow up, leave blank")
    followup_question = models.ForeignKey('QuestionType', related_name="parent_question", blank=True, null=True, help_text="If this question should result in a followup question, select the follow-up question. If not, leave blank") 
    expiry = models.IntegerField(default=1440, help_text="minutes until the question expires")
    sleep_offset = models.IntegerField(default=0, help_text="minutes after a user wakes up to send notification. if negative, it's minutes before a user goes to sleep to send a notification.")
    
    
    def __unicode__(self):
        return unicode( str(self.pk) + ": " + self.text )
        
    def optionList(self):
        return json.loads(self.params)
        
    def followup_question_parent(self):
        parents = self.parent_question.all()
        if len(parents) > 0:
            return parents[0]
        return None
    
class Baseline(models.Model):
    profile = models.OneToOneField('Profile', blank=True, null=True)
    ip = models.GenericIPAddressField()
    q1 = models.BooleanField(default=False)
    q2 = models.BooleanField(default=False)
    q3 = models.BooleanField(default=False)

class IphoneDummy(models.Model):
    email = models.EmailField()
    visits = models.IntegerField()
    datetime = models.DateTimeField(auto_now_add=True)
    hospital = models.IntegerField(blank=True, null=True)

class QuestionInstance(models.Model):
    question_type = models.ForeignKey('QuestionType')
    profile = models.ForeignKey('Profile')
    datetime = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    answer = models.IntegerField(blank=True, null=True)
    expired = models.BooleanField(default=False, help_text="Once an answer either expires past a certain time or is completed, this is checked off. This is for the efficiency of only querying the database on expired and profile.")
    notification_counter = models.IntegerField(default=0, help_text="How many times was a notification sent out for this Question Instance?")
#    followup_instance = models.ForeignKey('QuestionInstance', blank=True, null=True, help_text="If this question has a followup question associated, then reference it from here")
    def __unicode__(self):
        return str(self.datetime) + ": " +self.profile.__unicode__() + " (" +str(self.question_type.pk)+ ")"

GENDER_CHOICE = (
    ('m', 'Male'),
    ('f', 'Female'),
)
CENTER_CHOICE = (
    ('b', 'BWH'),
    ('m', 'MGH'),
    ('o', 'other'),
)
ETIOLOGY_CHOICE = (
    ('1', 'EtOH'),
    ('2', 'HCV'),
    ('3', 'NASH'),
    ('4', 'PBC'),
    ('5', 'PSC'),
    ('6', 'AIH'),
    ('7', 'A1AT'),
    ('8', 'Wilson'),
    ('9', 'Hemochromatosis'),
    ('10', 'HBV'),
    ('11', 'other'),
)
YN_CHOICE = (
    ('0', 'No'),
    ('1', 'Yes'),
    ('u', 'Unknown'),
)
YN_BLANK = (
    ('0', 'No'),
    ('1', 'Yes'),
    ('b', 'left blank'),
)
CARE_LOCATION_CHOICE = (
    ('h', 'hospital'),
    ('c', 'clinic'),
    ('e', 'emergency room'),
)
VISIT_TYPE_CHOICE = (
    ('r', 'routine'),
    ('u', 'urgent'),
)
        
class ChartBaseline(models.Model):
    study_id = models.CharField(max_length=15)
    last_name = models.CharField(max_length=20)
    mrn = models.CharField(max_length=9)
    created = models.DateTimeField(auto_now_add=True)
    dob = models.DateField(blank=True,null=True)
    dob2=  models.TextField(blank=True, null=True)
    date_of_enrollment = models.DateField(blank=True,null=True)
    date_of_enrollment2= models.TextField(blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICE)
    center = models.CharField(max_length=1, choices=CENTER_CHOICE)
    etiology = models.CharField(max_length=2, choices=ETIOLOGY_CHOICE)
    baseline_meld = models.IntegerField(blank=True, null=True)
    baseline_meld_insufficient = models.BooleanField(default=False) 
    baseline_child = models.IntegerField(blank=True, null=True)
    baseline_child_insufficient = models.BooleanField(default=False)
    transplant_candidate = models.CharField(max_length=1, choices=YN_CHOICE)
    hcc = models.CharField(max_length=1, choices=YN_CHOICE)
    aspirin81 = models.CharField(max_length=1, choices=YN_CHOICE)
    aspirin325 = models.CharField(max_length=1, choices=YN_CHOICE)
    other_antiplatelet = models.CharField(max_length=1, choices=YN_CHOICE)
    anticoagulant = models.CharField(max_length=1, choices=YN_CHOICE)
    date_first_liver_care = models.DateField(blank=True, null=True)
    date_first_liver_care2 = models.TextField(blank=True, null=True)
    date_last_liver_care_prior_to_study = models.DateField(blank=True, null=True)
    date_last_liver_care_prior_to_study2 = models.TextField(blank=True, null=True)
    location_last_liver_care_prior_to_study = models.CharField(max_length=1, choices=CARE_LOCATION_CHOICE)
    
    def __unicode__(self):
        return self.study_id + " : " + self.last_name
    
DISPOSITION_CHOICE = (
    ("a","admit"),
    ("h","home"),
    ("f","facility"),
)
    
class ChartA(models.Model):
    baseline= models.ForeignKey("ChartBaseline")
    date_of_liver_encounter = models.DateField(blank=True, null=True)
    date_of_liver_encounter2 =  models.TextField(blank=True, null=True)
    location_of_first_liver_encounter_since_study = models.CharField(max_length=1, choices=CENTER_CHOICE)
    if_clinic_q1_type = models.CharField(max_length=1, choices=VISIT_TYPE_CHOICE)
    if_clinic_q2_meld = models.IntegerField(blank=True, null=True)
    if_clinic_q2_meld_insufficient = models.BooleanField(default=False)
    if_emergency_room_q1_reason = models.TextField(blank=True, null=True)
    if_emergency_room_q1_disposition = models.CharField(max_length=1, choices=DISPOSITION_CHOICE)
    if_hospital_q1_admission_meld = models.IntegerField(blank=True, null=True)
    if_hospital_q1_admission_meld_insufficient = models.BooleanField(default=False)
    if_hospital_q2_admission_reason_Hepatic_Encephalopathy = models.BooleanField(default=False)
    if_hospital_q2_admission_reason_Ascites = models.BooleanField(default=False)
    if_hospital_q2_admission_reason_Acute_Kidney_Injury = models.BooleanField(default=False)
    if_hospital_q2_admission_reason_Esophageal_variceal_beed = models.BooleanField(default=False)
    if_hospital_q2_admission_reason_Non_esophageal_variceal_bleeding = models.BooleanField(default=False)
    if_hospital_q2_admission_reason_Infection = models.BooleanField(default=False)
    if_hospital_q2_admission_reason_Fluid_overload = models.BooleanField(default=False)
    if_hospital_q3_discharge_meld = models.IntegerField(blank=True, null=True)
    if_hospital_q3_discharge_meld_insufficient = models.BooleanField(default=False)
    if_hospital_q4_disposition = models.CharField(max_length=1, choices=DISPOSITION_CHOICE)
    created = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        if self.date_of_liver_encounter:
            return self.baseline.__unicode__() + " : " + str(self.date_of_liver_encounter)
        if self.date_of_liver_encounter2:
            return self.baseline.__unicode__() + " : " + str(self.date_of_liver_encounter2)
        return self.baseline.__unicode__()
            
    
class ChartB(models.Model):
    baseline= models.ForeignKey("ChartBaseline")
    date_of_telephone_encounter = models.DateField(blank=True, null=True)
    date_of_telephone_encounter2 =  models.TextField(blank=True, null=True)
    reason= models.TextField(blank=True, null=True)
    outcome = models.TextField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        if self.date_of_telephone_encounter:
            return self.baseline.__unicode__() + " : " + str(self.date_of_telephone_encounter)
        if self.date_of_telephone_encounter2:
            return self.baseline.__unicode__() + " : " + str(self.date_of_telephone_encounter2)
        return self.baseline.__unicode__()
    
class ChartC(models.Model):
    baseline= models.ForeignKey("ChartBaseline")
    date_terminated = models.DateField(blank=True, null=True)
    date_terminated2 =  models.TextField(blank=True, null=True)
    date_transplanted = models.DateField(blank=True, null=True)
    date_transplanted2 =  models.TextField(blank=True, null=True)
    date_deceased = models.DateField(blank=True, null=True)
    date_deceased2 =  models.TextField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return self.baseline.__unicode__()
    
LANGUAGE_CHOICE = (
    ('e', 'English'),
    ('s', 'Spanish'),
    ('o', 'Other'),
)
MARITAL_CHOICE = (
    ('s','single'),
    ('m', 'married'),
    ('d', 'divorced'),
    ('w', 'widowed'),
    ('o', 'other'),
    ('l', 'left blank')
)
LIVE_WITH_CHOICE = (
    ('a','alone'),
    ('s', 'significant other'),
    ('c', 'adult children'),
    ('f', 'family'),
    ('p', 'parent(s)'),
    ('o', 'other'),
    ('l', 'left blank')
)
OCCUPATION_CHOICE = (
    ('e', 'employed'),
    ('u', 'unemployed'),
    ('r', 'retired'),
    ('d', 'disabled'),
    ('o', 'other'),
    ('l', 'left blank')
)
WORK_DAYS_CHOICE = (
    ('1', 'day'),
    ('2', 'evening'),
    ('3', 'nights'),
    ('4', 'other'),
    ('5', 'not working'),
    ('6', 'left blank')
)
FREQ_CHOICE0 = (
    ('1', 'always'),
    ('2', 'usually'),
    ('3', 'rarely'),
    ('4', 'never'),
    ('5', 'unsure'),
    ('6', 'left blank'),
)
FREQ_CHOICE = (
    ('1', 'never'),
    ('2', 'several days'),
    ('3', 'everyday'),
    ('6', 'left blank'),
)
FREQ_CHOICE2 = (
    ('1', 'at least once a week'),
    ('2', '1-3 times a month'),
    ('3', 'less than once a month'),
    ('4', 'unsure'),
    ('6', 'left blank'),
)
FREQ_CHOICE3 = (
    ('1', 'at least every 3 months'),
    ('2', 'at least every 6 months'),
    ('3', 'unsure'),
    ('6', 'left blank'),
)
FREQ_CHOICE4 = (
    ('1', 'never'),
    ('2', 'rarely'),
    ('3', 'sometimes'),
    ('4', 'usually'),
    ('5', 'unsure'),
    ('6', 'left blank'),
)
DRINK_CHOICE = (
    ('1', 'none'),
    ('2', '0-1 /month'),
    ('3', '2-4/month'),
    ('4', '2-3/week'),
    ('5', '4 or more per week'),
)
CELL_CHOICE1 = (
    ('1','less than 60 minutes a day'),
    ('2','between 1 and 3 hours a day'),
    ('3','between 3 and 5 hours a day'),
    ('4','morethan 5 hours a day'),
    ('5','left blank'),
)
CELL_CHOICE2 = (
    ('1','less than every 1 minutes'),
    ('2','every 10 minutes'),
    ('3','every 30 minutes'),
    ('4','once an hour'),
    ('5','once a few times a day'),
    ('6','once a day orless'),
    ('7','left blank'),
)
CELL_CHOICE3 = (
    ('1','in the bedroom'),
    ('2','next to my bed'),
    ('3','in a different room from where I sleep'),
    ('4','other location'),
    ('5','left blank'),
)
EDUCATION_CHOICE = (
    ('1','less than high school'),
    ('2','high school diploma'),
    ('3','college degree'),
    ('4','graduate degree'),
    ('5','left blank'),
)
    
class BaselineQuestionaire(models.Model):
    study_id = models.CharField(max_length=15)
    last_name = models.CharField(max_length=20)
    mrn = models.CharField(max_length=9)
    created = models.DateTimeField(auto_now_add=True)
    dob = models.DateField(blank=True,null=True)
    dob2=  models.TextField(blank=True, null=True)
    date_of_enrollment = models.DateField(blank=True,null=True)
    date_of_enrollment2= models.TextField(blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICE)
    center = models.CharField(max_length=1, choices=CENTER_CHOICE)
    date_of_questionaire = models.DateField(blank=True,null=True)
    date_of_questionaire2= models.TextField(blank=True, null=True)
    primary_language = models.CharField(max_length=1, choices=LANGUAGE_CHOICE)
    understand_english = models.CharField(max_length=1, choices=YN_BLANK)
    highest_level_of_education = models.CharField(max_length=1, choices=EDUCATION_CHOICE)
    marital_status =  models.CharField(max_length=1, choices=MARITAL_CHOICE)
    who_do_you_live_with =  models.CharField(max_length=1, choices=LIVE_WITH_CHOICE)
    occupation =  models.CharField(max_length=1, choices=OCCUPATION_CHOICE)
    work_days_evenings_nights =  models.CharField(max_length=1, choices=WORK_DAYS_CHOICE)
    advanced_care_directives =  models.CharField(max_length=1, choices=YN_BLANK)
    anemia = models.CharField(max_length=1, choices=YN_BLANK)
    arthritis = models.CharField(max_length=1, choices=YN_BLANK)
    cancer = models.CharField(max_length=1, choices=YN_BLANK)
    cancer_type_and_location = models.TextField(blank=True,null=True)
    copd = models.CharField(max_length=1, choices=YN_BLANK)
    diabetes = models.CharField(max_length=1, choices=YN_BLANK)
    depression_anxiety = models.CharField(max_length=1, choices=YN_BLANK)
    kidney_disease = models.CharField(max_length=1, choices=YN_BLANK)
    heart_disease = models.CharField(max_length=1, choices=YN_BLANK)
    obesity = models.CharField(max_length=1, choices=YN_BLANK)
    osteoporosis = models.CharField(max_length=1, choices=YN_BLANK)
    sleep_apnia = models.CharField(max_length=1, choices=YN_BLANK)
    stroke = models.CharField(max_length=1, choices=YN_BLANK)
    how_often_liver_medications = models.CharField(max_length=1, choices=FREQ_CHOICE0)
    how_often_non_liver_medications = models.CharField(max_length=1, choices=FREQ_CHOICE0)
    how_often_blood_work = models.CharField(max_length=1, choices=FREQ_CHOICE2)
    how_often_radiology = models.CharField(max_length=1, choices=FREQ_CHOICE3)
    how_often_procedures = models.CharField(max_length=1, choices=FREQ_CHOICE2)
    how_often_miss_appt = models.CharField(max_length=1, choices=FREQ_CHOICE4)
    check_weight = models.CharField(max_length=1, choices=YN_BLANK)
    check_fluid = models.CharField(max_length=1, choices=YN_BLANK)
    check_bowel_movements = models.CharField(max_length=1, choices=YN_BLANK)
    adjust_medications = models.CharField(max_length=1, choices=YN_BLANK)
    check_bleeding_bruises = models.CharField(max_length=1, choices=YN_BLANK)
    contact_md = models.CharField(max_length=1, choices=YN_BLANK)
    currently_smoke = models.CharField(max_length=1, choices=YN_BLANK)
    past_smoke = models.CharField(max_length=1, choices=YN_BLANK)
    how_many_cigs_daily = models.TextField(blank=True,null=True)
    when_quit = models.DateField(blank=True,null=True)
    when_quit2 = models.TextField(blank=True,null=True)
    alcohol = models.CharField(max_length=1, choices=YN_BLANK)
    average_drinks_per_year = models.CharField(max_length=1, choices=DRINK_CHOICE)
    drugs = models.CharField(max_length=1, choices=YN_BLANK)
    what_drugs = models.TextField(blank=True,null=True)
    exercise = models.CharField(max_length=1, choices=YN_BLANK)
    what_often = models.TextField(blank=True,null=True)
    work_day_time = models.IntegerField(blank=True,null=True)
    non_work_day_time = models.IntegerField(blank=True,null=True)
    prevent_activities = models.TextField(blank=True,null=True)
    six_month_health = models.CharField(max_length=1, choices=YN_BLANK)
    six_month_health2 = models.TextField(blank=True,null=True)
    particular_diet = models.CharField(max_length=1, choices=YN_BLANK)
    diet_choices_low_calorie = models.BooleanField(default=False)
    diet_choices_low_fat = models.BooleanField(default=False)
    diet_choices_low_salt = models.BooleanField(default=False)
    diet_choices_low_sugar = models.BooleanField(default=False)
    diet_choices_high_protein = models.BooleanField(default=False)
    diet_choices_high_in_fruits_and_veggies = models.BooleanField(default=False)
    diet_choices_other = models.BooleanField(default=False)
    diet_choices_other2 = models.TextField(blank=True,null=True)
    diet_choices_I_have_not_been_given_any_diet_advice = models.BooleanField(default=False)
    average_sleep_weeknight = models.IntegerField(blank=True,null=True)
    average_sleep_weekend = models.IntegerField(blank=True,null=True)
    naps_weekdays = models.CharField(max_length=1, choices=YN_BLANK)
    naps_weekends = models.CharField(max_length=1, choices=YN_BLANK)
    sleep_cycle_issues = models.CharField(max_length=1, choices=YN_BLANK)
    sleep_pill = models.CharField(max_length=1, choices=YN_BLANK)
    cpap = models.CharField(max_length=1, choices=YN_BLANK)
    fall_asleep_day = models.CharField(max_length=1, choices=YN_BLANK)
    little_interest = models.CharField(max_length=1, choices=FREQ_CHOICE)
    feeling_down = models.CharField(max_length=1, choices=FREQ_CHOICE)
    trouble_sleeping = models.CharField(max_length=1, choices=FREQ_CHOICE)
    tired_energy = models.CharField(max_length=1, choices=FREQ_CHOICE)
    irritated = models.CharField(max_length=1, choices=FREQ_CHOICE)
    poor_appetite = models.CharField(max_length=1, choices=FREQ_CHOICE)
    trouble_concentrating = models.CharField(max_length=1, choices=FREQ_CHOICE)
    little_interest = models.CharField(max_length=1, choices=FREQ_CHOICE)
    speaking_moving_slow = models.CharField(max_length=1, choices=FREQ_CHOICE)
    trouble_words_misplacing = models.CharField(max_length=1, choices=FREQ_CHOICE)
    cell_phone_use = models.CharField(max_length=1, choices=CELL_CHOICE1)
    cell_phone_check = models.CharField(max_length=1, choices=CELL_CHOICE2)
    cell_phone_sleep = models.CharField(max_length=1, choices=CELL_CHOICE3)
    cell_tasks_watching_tv_or_movie = models.BooleanField(default=False)
    cell_tasks_attending_a_social_event = models.BooleanField(default=False)
    cell_tasks_riding_public_transportation = models.BooleanField(default=False)
    cell_tasks_eating_at_home_or_restaurant = models.BooleanField(default=False)
    cell_tasks_driving_a_car = models.BooleanField(default=False)
    health_app_on_cell_phone_frequency = models.CharField(max_length=1, choices=FREQ_CHOICE)
    physical_activity= models.IntegerField(blank=True,null=True)
    dietary_habits = models.IntegerField(blank=True,null=True)
    amount_and_quantity_sleep = models.IntegerField(blank=True,null=True)
    social_interactions = models.IntegerField(blank=True,null=True)
    smartphone_daily_entry = models.IntegerField(blank=True,null=True)
    cell_phone_talk_text_daily = models.IntegerField(blank=True,null=True)
    people_interact_daily = models.IntegerField(blank=True,null=True)
    current_communication_phone = models.BooleanField(default=False)
    current_communication_email = models.BooleanField(default=False)
    current_communication_gateway = models.BooleanField(default=False)
    current_communication_text = models.BooleanField(default=False)
    current_communication_letter = models.BooleanField(default=False)
    current_communication_in_person_during_scheduled_visits = models.BooleanField(default=False)
    current_communication_in_person_by_stopping_by_front_desk = models.BooleanField(default=False)
    preferred_communication_phone =models.BooleanField(default=False)
    preferred_communication_email =models.BooleanField(default=False)
    preferred_communication_other =models.BooleanField(default=False)
    preferred_communication_other2 =models.TextField(blank=True,null=True)

    def __unicode__(self):
        return self.study_id + " : " + self.last_name
