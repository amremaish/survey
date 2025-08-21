from django.urls import path
from .views import (
    InvitationCreateView,
    SessionStartView, SessionAutosaveView, SessionCompleteView
)

urlpatterns = [
    # invitations
    path("surveys/<int:survey_id>/invitations/", InvitationCreateView.as_view(), name="invitation-create"),

    # sessions
    path("sessions/start/", SessionStartView.as_view(), name="session-start"),
    path("sessions/<int:session_id>/autosave/", SessionAutosaveView.as_view(), name="session-autosave"),
    path("sessions/<int:session_id>/complete/", SessionCompleteView.as_view(), name="session-complete"),
]
