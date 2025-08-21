from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # JWT endpoints
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/token/verify/", TokenVerifyView.as_view(), name="token_verify"),

    # your APIs
    path("api/v1/surveys/", include("apps.surveys.urls")),
    path("api/v1/sessions/", include("apps.survey_sessions.urls")),
    path("api/v1/responses/", include("apps.responses.urls")),
    path("api/v1/", include("apps.accounts.urls")),
]
