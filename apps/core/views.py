from django.shortcuts import render
from django.utils import timezone
from apps.surveys.models import Survey, SurveyInvitation, InvitationStatus

def survey_builder(request):
    return render(request, "builder.html")

def survey_runner(request, survey_code: str | None = None):
    return render(request, "runner.html", {"survey_code": survey_code or ""})

def public_runner(request, survey_code: str):
    token = request.GET.get("token")
    status_flag = "invalid" if not token else None
    if token:
        try:
            survey = Survey.objects.filter(code=survey_code).first()
            inv = SurveyInvitation.objects.filter(token=token, survey=survey).first()
            if inv:
                if inv.status == InvitationStatus.SUBMITTED:
                    status_flag = "submitted"
                elif inv.expires_at and inv.expires_at < timezone.now():
                    status_flag = "expired"
        except Exception:
            status_flag = None
    return render(request, "public_runner.html", {"survey_code": survey_code, "invite_status": status_flag or ""})


def org_manager(request):
    return render(request, "organizations.html")
def org_users(request, org_id: int):
    return render(request, "org_users.html", {"org_id": org_id})

def org_dashboard(request, org_id: int):
    return render(request, "org_dashboard.html", {"org_id": org_id})

def surveys_manager(request):
    return render(request, "surveys.html")