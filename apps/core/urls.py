from django.urls import path
from .views import index, survey_builder, org_manager, surveys_manager, public_runner, org_users, org_dashboard, org_dashboard_login, login_view

urlpatterns = [
    path("", index, name="index"),
    path("builder", survey_builder, name="survey-builder"),
    path("survey/<slug:survey_code>", public_runner, name="public-runner"),
    path("orgs/", org_manager, name="org-manager"),
    path("surveys/", surveys_manager, name="surveys-manager"),
    path("users/<int:org_id>", org_users, name="org-users"),
    path("dashboard/<int:org_id>", org_dashboard, name="org-dashboard"),
    path("dashboard/login", org_dashboard_login, name="org-dashboard-login"),
    path("login", login_view, name="login"),
]
