from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/surveys/", include("apps.surveys.urls")),
    path("api/v1/sessions/", include("apps.survey_sessions.urls")),
    path("api/v1/", include("apps.accounts.urls")),
]
