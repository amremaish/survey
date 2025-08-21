from django.urls import path
from .views import OrganizationListCreateView, OrganizationAddUserView

urlpatterns = [
    path("orgs/", OrganizationListCreateView.as_view(), name="org-list-create"),
    path("orgs/<int:org_id>/users/", OrganizationAddUserView.as_view(), name="org-add-user"),
]
