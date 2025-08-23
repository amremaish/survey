from django.urls import path
from .views import survey_builder, survey_runner, org_manager, surveys_manager, public_runner, org_users, org_dashboard

urlpatterns = [
    path("", survey_builder, name="survey-builder"),
    path("run/", survey_runner, name="survey-runner"),
    path("run/<slug:survey_code>", survey_runner, name="survey-runner-code"),
    path("survey/<slug:survey_code>", public_runner, name="public-runner"),
    path("orgs/", org_manager, name="org-manager"),
    path("surveys/", surveys_manager, name="surveys-manager"),
    path("users/<int:org_id>", org_users, name="org-users"),
    path("dashboard/<int:org_id>", org_dashboard, name="org-dashboard"),
]
