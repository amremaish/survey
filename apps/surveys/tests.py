from django.test import TestCase
from rest_framework.test import APIClient
from apps.surveys.models import Survey, SurveyStatus, SurveySection, SurveyQuestion
from apps.accounts.models import Organization, Role
from django.contrib.auth.models import User


class SurveysApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="viewer", password="pass")
        Role.objects.create(name="Viewer").users.add(self.user)
        self.client.force_authenticate(user=self.user)
        org = Organization.objects.create(name="Org A")
        self.survey = Survey.objects.create(organization=org, code="code-1", title="T1", status=SurveyStatus.ACTIVE)

    def test_detail_by_code(self):
        resp = self.client.get(f"/api/v1/surveys/code/{self.survey.code}/detail/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body.get("id"), self.survey.id)
        self.assertEqual(body.get("title"), self.survey.title)

    def test_list_requires_viewer(self):
        # user already has Viewer
        resp = self.client.get("/api/v1/surveys/")
        self.assertEqual(resp.status_code, 200)

    def test_create_requires_editor(self):
        # remove viewer, re-auth with plain user
        self.client.force_authenticate(user=None)
        u = User.objects.create_user(username="creator", password="p")
        self.client.force_authenticate(user=u)
        payload = {"title": "S", "organization_id": self.survey.organization_id, "status": SurveyStatus.ACTIVE}
        resp = self.client.post("/api/v1/surveys/", payload, format='json')
        self.assertEqual(resp.status_code, 403)
        # add Editor
        Role.objects.get_or_create(name="Editor")[0].users.add(u)
        resp2 = self.client.post("/api/v1/surveys/", payload, format='json')
        self.assertEqual(resp2.status_code, 201)
