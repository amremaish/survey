from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from apps.accounts.models import Role
from apps.surveys.models import Survey, SurveyStatus, SurveyInvitation, InvitationStatus
from apps.responses.models import SurveyResponse
from django.utils import timezone


class AnalyticsApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="viewer", password="pass1234")
        role = Role.objects.create(name="Viewer")
        role.users.add(self.user)
        self.client.force_authenticate(user=self.user)
        # minimal survey + response
        from apps.accounts.models import Organization
        org = Organization.objects.create(name="Org A")
        self.survey = Survey.objects.create(organization=org, code="s-1", title="S1", status=SurveyStatus.ACTIVE)
        SurveyResponse.objects.create(survey=self.survey, submitted_at=timezone.now())

    def test_overall_submissions_ok(self):
        resp = self.client.get("/api/v1/analytics/overall-submissions/?window=day&days=7")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("labels", data)
        self.assertIn("data", data)

    def test_submissions_by_organization(self):
        from apps.accounts.models import Organization
        org_b = Organization.objects.create(name="Org B")
        survey_b = Survey.objects.create(organization=org_b, code="s-2", title="S2", status=SurveyStatus.ACTIVE)
        SurveyResponse.objects.create(survey=survey_b, submitted_at=timezone.now())
        SurveyResponse.objects.create(survey=survey_b, submitted_at=timezone.now())
        resp = self.client.get("/api/v1/analytics/submissions-by-organization/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("labels", body)
        self.assertIn("data", body)

    def test_invitation_status(self):
        from apps.accounts.models import Organization
        org = Organization.objects.first()
        SurveyInvitation.objects.create(organization=org, survey=self.survey, email="a@x.com", token="t1", expires_at=timezone.now(), status=InvitationStatus.PENDING)
        SurveyInvitation.objects.create(organization=org, survey=self.survey, email="b@x.com", token="t2", expires_at=timezone.now(), status=InvitationStatus.SUBMITTED)
        SurveyInvitation.objects.create(organization=org, survey=self.survey, email="c@x.com", token="t3", expires_at=timezone.now(), status=InvitationStatus.EXPIRED)
        resp = self.client.get("/api/v1/analytics/invitation-status/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body.get("labels", [])), 3)
        self.assertEqual(len(body.get("data", [])), 3)

    def test_responses_by_survey_status(self):
        from apps.accounts.models import Organization
        org = Organization.objects.first()
        s_draft = Survey.objects.create(organization=org, code="sd", title="D", status=SurveyStatus.DRAFT)
        s_arch = Survey.objects.create(organization=org, code="sa", title="A", status=SurveyStatus.ARCHIVED)
        SurveyResponse.objects.create(survey=s_draft, submitted_at=timezone.now())
        SurveyResponse.objects.create(survey=s_arch, submitted_at=timezone.now())
        resp = self.client.get("/api/v1/analytics/responses-by-survey-status/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body.get("labels", [])), 3)
        self.assertEqual(len(body.get("data", [])), 3)
