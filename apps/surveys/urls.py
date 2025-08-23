from django.urls import path
from .views import (
    SurveyListCreateView, SurveyDetailView, SurveyDetailByCodeView,
    SectionCreateView, QuestionCreateView, OptionCreateView,
    QuestionUpdateView, QuestionDetailView, InvitationListCreateView
)

urlpatterns = [
    path("", SurveyListCreateView.as_view(), name="survey-list-create"),
    path("<int:survey_id>/detail/", SurveyDetailView.as_view(), name="survey-detail"),
    path("code/<slug:survey_code>/detail/", SurveyDetailByCodeView.as_view(), name="survey-detail-code"),
    path("<int:survey_id>/sections/", SectionCreateView.as_view(), name="section-create"),
    path("sections/<int:section_id>/questions/", QuestionCreateView.as_view(), name="question-create"),
    path("questions/<int:question_id>/", QuestionUpdateView.as_view(), name="question-update"),
    path("questions/<int:question_id>/detail/", QuestionDetailView.as_view(), name="question-detail"),
    path("questions/<int:question_id>/options/", OptionCreateView.as_view(), name="option-create"),
    path("<int:survey_id>/invitations/", InvitationListCreateView.as_view(), name="invitation-list-create"),
]
