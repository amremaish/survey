from django.contrib import admin
from .models import Survey, SurveySection, SurveyQuestion, SurveyQuestionOption, QuestionDependency, LogicRule

admin.site.register(Survey)
admin.site.register(SurveySection)
admin.site.register(SurveyQuestion)
admin.site.register(SurveyQuestionOption)
admin.site.register(QuestionDependency)
admin.site.register(LogicRule)
