from django.urls import path
from .views import (
    SessionStartView, SessionAutosaveView, SessionCompleteView, SessionDetailView
)

urlpatterns = [
    # sessions
    path("sessions/start/", SessionStartView.as_view(), name="session-start"),
    path("sessions/<int:session_id>/", SessionDetailView.as_view(), name="session-detail"),
    path("sessions/<int:session_id>/autosave/", SessionAutosaveView.as_view(), name="session-autosave"),
    path("sessions/<int:session_id>/complete/", SessionCompleteView.as_view(), name="session-complete"),
]
