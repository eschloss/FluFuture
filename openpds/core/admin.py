from openpds.core.models import *
from django.contrib import admin

def resetDays(modeladmin, request, queryset):
    for q in queryset:
        if q.start and q.end:
            days = int((int(q.end.strftime("%s")) - int(q.start.strftime("%s"))) / 60.0/60.0/24.0)
            if q.days != days:
                q.days = days
                q.save()
resetDays.short_description = "Reset Days based on start and end"

class Emoji2Admin(admin.ModelAdmin):
    list_display = ['profile', 'emoji', 'created']
    search_fields = ['profile__uuid', 'emoji', 'created']
class ProfileStartEndAdmin(admin.ModelAdmin):
    list_display = ['profile', 'start', 'end', 'days']
    search_fields = ['profile__uuid', 'start', 'end', 'days']
    actions = [resetDays,]
class FluQuestionsAdmin(admin.ModelAdmin):
    list_display = ['profile', 'fluThisSeason', 'fluLastSeason', 'vaccineThisSeason']
    search_fields = ['profile__uuid',]
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['uuid', 'created']
    search_fields = ['uuid']
class BaselineAdmin(admin.ModelAdmin):
    list_display = ['profile', 'ip']
    search_fields = ['profile__uuid', 'ip']
class DummyAdmin(admin.ModelAdmin):
    list_display = ['email', 'datetime', 'visits', 'hospital']

admin.site.register(Profile, ProfileAdmin)
admin.site.register(FB_Connection)
admin.site.register(Emoji, Emoji2Admin)
admin.site.register(Emoji2, Emoji2Admin)
admin.site.register(Device)
admin.site.register(QuestionInstance)
admin.site.register(QuestionType)
admin.site.register(FirebaseToken)
admin.site.register(IPReferral)
admin.site.register(AuditEntry)
admin.site.register(ProfileStartEnd, ProfileStartEndAdmin)
admin.site.register(FluQuestions, FluQuestionsAdmin)
admin.site.register(Baseline, BaselineAdmin)
admin.site.register(IphoneDummy, DummyAdmin)
