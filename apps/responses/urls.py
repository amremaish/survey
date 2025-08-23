from django.urls import path
from .views import SubmitResponseView, ResponseDetailView, OrgResponsesDashboardView

urlpatterns = [
    path("submit/", SubmitResponseView.as_view(), name="response-submit"),
    path("<int:response_id>/", ResponseDetailView.as_view(), name="response-detail"),
    path("org/<int:org_id>/dashboard/", OrgResponsesDashboardView.as_view(), name="org-responses-dashboard"),
]
