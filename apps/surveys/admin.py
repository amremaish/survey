from django.contrib import admin
from .models import Survey, SurveySection, SurveyQuestion, SurveyQuestionOption

admin.site.register(Survey)
admin.site.register(SurveySection)
admin.site.register(SurveyQuestion)
admin.site.register(SurveyQuestionOption)
