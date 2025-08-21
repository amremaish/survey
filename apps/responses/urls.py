from django.urls import path
from .views import SubmitResponseView, ResponseDetailView

urlpatterns = [
    path("submit/", SubmitResponseView.as_view(), name="response-submit"),
    path("<int:response_id>/", ResponseDetailView.as_view(), name="response-detail"),
]
