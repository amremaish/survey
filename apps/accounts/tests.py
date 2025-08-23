from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from apps.accounts.models import Role


class AccountsApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="acct", password="pass1234")
        self.client.force_authenticate(user=self.user)

    def test_me_requires_auth(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get("/api/v1/me/")
        self.assertEqual(resp.status_code, 401)

    def test_me_returns_basic_info_with_roles(self):
        # assign a role to ensure roles array present
        role = Role.objects.create(name="Viewer")
        role.users.add(self.user)
        self.client.force_authenticate(user=self.user)
        resp = self.client.get("/api/v1/me/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("username"), "acct")
        self.assertIn("roles", data)

    def test_org_list_requires_viewer_role(self):
        resp = self.client.get("/api/v1/orgs/")
        self.assertEqual(resp.status_code, 403)
        Role.objects.get_or_create(name="Viewer")[0].users.add(self.user)
        resp = self.client.get("/api/v1/orgs/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("count", resp.json())

    def test_org_create_requires_editor_role(self):
        Role.objects.get_or_create(name="Viewer")[0].users.add(self.user)
        payload = {"name": "Org Created"}
        resp = self.client.post("/api/v1/orgs/", payload, format="json")
        self.assertEqual(resp.status_code, 403)
        Role.objects.get_or_create(name="Editor")[0].users.add(self.user)
        resp2 = self.client.post("/api/v1/orgs/", payload, format="json")
        self.assertEqual(resp2.status_code, 201)
        self.assertEqual(resp2.json().get("name"), "Org Created")

    def test_org_detail_get_with_viewer(self):
        from apps.accounts.models import Organization
        org = Organization.objects.create(name="Org D")
        Role.objects.get_or_create(name="Viewer")[0].users.add(self.user)
        resp = self.client.get(f"/api/v1/orgs/{org.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("name"), "Org D")

    def test_org_members_list_requires_viewer(self):
        from apps.accounts.models import Organization, OrganizationMember
        org = Organization.objects.create(name="Org M")
        resp = self.client.get(f"/api/v1/orgs/{org.id}/members/")
        self.assertEqual(resp.status_code, 403)
        Role.objects.get_or_create(name="Viewer")[0].users.add(self.user)
        member_user = User.objects.create_user(username="member", password="p")
        OrganizationMember.objects.create(organization=org, user=member_user)
        resp2 = self.client.get(f"/api/v1/orgs/{org.id}/members/")
        self.assertEqual(resp2.status_code, 200)
        self.assertIn("results", resp2.json())

    def test_org_member_delete_requires_editor(self):
        from apps.accounts.models import Organization, OrganizationMember
        org = Organization.objects.create(name="Org X")
        victim = User.objects.create_user(username="victim", password="p")
        mem = OrganizationMember.objects.create(organization=org, user=victim)
        Role.objects.get_or_create(name="Viewer")[0].users.add(self.user)
        resp = self.client.delete(f"/api/v1/orgs/{org.id}/members/{mem.id}/")
        self.assertEqual(resp.status_code, 403)
        Role.objects.get_or_create(name="Editor")[0].users.add(self.user)
        resp2 = self.client.delete(f"/api/v1/orgs/{org.id}/members/{mem.id}/")
        self.assertEqual(resp2.status_code, 204)
