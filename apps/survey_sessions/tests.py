from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from apps.accounts.models import Organization
from apps.surveys.models import Survey, SurveyStatus


class SurveyResponsesApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="u", password="p")
        self.client.force_authenticate(user=self.user)
        self.org = Organization.objects.create(name="Org")
        self.survey = Survey.objects.create(organization=self.org, code="code-x", title="S", status=SurveyStatus.ACTIVE)

    def test_start_session_ok(self):
        resp = self.client.post("/api/v1/sessions/sessions/start/", {"survey_id": self.survey.id, "organization_id": self.org.id}, format='json')
        self.assertIn(resp.status_code, (200, 201))
        body = resp.json()
        self.assertIn("id", body)

    def test_get_session(self):
        resp = self.client.post("/api/v1/sessions/sessions/start/", {"survey_id": self.survey.id}, format='json')
        sid = resp.json()["id"]
        resp2 = self.client.get(f"/api/v1/sessions/sessions/{sid}/")
        self.assertEqual(resp2.status_code, 200)