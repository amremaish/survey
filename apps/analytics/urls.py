from django.urls import path
from .views import OverallSubmissionsView, SubmissionsByOrganizationView, InvitationStatusView, ResponsesBySurveyStatusView


urlpatterns = [
    path("overall-submissions/", OverallSubmissionsView.as_view(), name="overall-submissions"),
    path("submissions-by-organization/", SubmissionsByOrganizationView.as_view(), name="submissions-by-organization"),
    path("invitation-status/", InvitationStatusView.as_view(), name="invitation-status"),
    path("responses-by-survey-status/", ResponsesBySurveyStatusView.as_view(), name="responses-by-survey-status"),
]


