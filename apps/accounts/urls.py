from django.urls import path
from .views import OrganizationListCreateView, OrganizationDetailView, OrgMembersView, OrgMemberDetailView, MyOrganizationsView, MeView

urlpatterns = [
    path("orgs/", OrganizationListCreateView.as_view(), name="org-list-create"),
    path("orgs/<int:org_id>/", OrganizationDetailView.as_view(), name="org-detail"),
    path("orgs/<int:org_id>/members/", OrgMembersView.as_view(), name="org-members"),
    path("orgs/<int:org_id>/members/<int:member_id>/", OrgMemberDetailView.as_view(), name="org-member-detail"),
    path("my-orgs/", MyOrganizationsView.as_view(), name="my-organizations"),
    path("me/", MeView.as_view(), name="me"),
]
