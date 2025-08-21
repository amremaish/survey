from django.urls import path
from .views import (
    SurveyListCreateView, SurveyDetailView,
    SectionCreateView, QuestionCreateView, OptionCreateView,
    LogicRuleCreateView
)

urlpatterns = [
    path("", SurveyListCreateView.as_view(), name="survey-list-create"),
    path("<int:survey_id>/detail/", SurveyDetailView.as_view(), name="survey-detail"),
    path("<int:survey_id>/sections/", SectionCreateView.as_view(), name="section-create"),
    path("<int:survey_id>/logic/", LogicRuleCreateView.as_view(), name="logic-create"),
    path("sections/<int:section_id>/questions/", QuestionCreateView.as_view(), name="question-create"),
    path("questions/<int:question_id>/options/", OptionCreateView.as_view(), name="option-create"),
]
