from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from apps.accounts.models import Organization, OrganizationMember, Role
from apps.surveys.models import Survey, SurveyStatus
from apps.responses.models import SurveyResponse
from apps.surveys.models import SurveySection, SurveyQuestion, QuestionType


class SurveyResponsesApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="user", password="pass")
        Role.objects.get_or_create(name="Viewer")[0].users.add(self.user)
        self.client.force_authenticate(user=self.user)
        self.org = Organization.objects.create(name="OrgR")
        OrganizationMember.objects.create(organization=self.org, user=self.user)
        self.survey = Survey.objects.create(organization=self.org, code="sub-code", title="Submit Test", status=SurveyStatus.ACTIVE)
        self.section = SurveySection.objects.create(survey=self.survey, title="Sec", sort_order=1)
        self.q1 = SurveyQuestion.objects.create(section=self.section, code="q-1", input_title="Name", type=QuestionType.TEXT, required=True, sensitive=False, constraints={}, sort_order=1, metadata={})

    def test_submit_direct_success(self):
        payload = {"survey_id": self.survey.id, "answers": {"q-1": "Alice"}}
        resp = self.client.post("/api/v1/responses/submit/", payload, format='json')
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertIn("id", body)
        self.assertEqual(body.get("survey"), self.survey.id)
        self.assertTrue(len(body.get("answers", [])) >= 1)

    def test_submit_session_success(self):
        # start a session and then submit via session_id
        sresp = self.client.post("/api/v1/sessions/sessions/start/", {"survey_id": self.survey.id}, format='json')
        self.assertIn(sresp.status_code, (200, 201))
        sid = sresp.json()["id"]
        resp = self.client.post("/api/v1/responses/submit/", {"session_id": sid, "answers": {"q-1": "Bob"}}, format='json')
        self.assertEqual(resp.status_code, 201)

    def test_submit_inactive_survey_blocked(self):
        survey_draft = Survey.objects.create(organization=self.org, code="sub-draft", title="Draft", status=SurveyStatus.DRAFT)
        sec = SurveySection.objects.create(survey=survey_draft, title="S", sort_order=1)
        SurveyQuestion.objects.create(section=sec, code="q-1", input_title="Name", type=QuestionType.TEXT, required=True, sensitive=False, constraints={}, sort_order=1, metadata={})
        resp = self.client.post("/api/v1/responses/submit/", {"survey_id": survey_draft.id, "answers": {"q-1": "X"}}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_org_dashboard_forbidden_without_membership(self):
        # New user without membership
        outsider = User.objects.create_user(username="outsider", password="p")
        Role.objects.get_or_create(name="Viewer")[0].users.add(outsider)
        self.client.force_authenticate(user=outsider)
        resp = self.client.get(f"/api/v1/responses/org/{self.org.id}/dashboard/")
        self.assertEqual(resp.status_code, 403)

    def test_response_detail_requires_same_org(self):
        # Create another user in same org -> allowed
        other = User.objects.create_user(username="other", password="p")
        Role.objects.get_or_create(name="Viewer")[0].users.add(other)
        OrganizationMember.objects.create(organization=self.org, user=other)
        self.client.force_authenticate(user=other)
        # create a response to fetch
        resp_obj = SurveyResponse.objects.create(survey=self.survey)
        resp = self.client.get(f"/api/v1/responses/{resp_obj.id}/")
        self.assertEqual(resp.status_code, 200)

        # outsider not in org -> 403
        outsider = User.objects.create_user(username="outsider2", password="p")
        self.client.force_authenticate(user=outsider)
        resp2 = self.client.get(f"/api/v1/responses/{resp_obj.id}/")
        self.assertEqual(resp2.status_code, 403)
