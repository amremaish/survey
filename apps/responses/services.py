from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Tuple

from django.db import transaction
from django.shortcuts import get_object_or_404

from apps.surveys.models import Survey, SurveyQuestion, SurveyQuestionOption, QuestionType
from apps.survey_sessions.models import SurveySession, SurveyInvitation, SessionStatus
from .models import SurveyResponse, SurveyAnswer, CryptoKey

def _encrypt_if_needed(value: Any) -> bytes:
    """
    Stub encryption. Replace with real encryption (KMS/HSM/Fernet/etc.).
    For now, we just convert to bytes for demonstration.
    """
    if value is None:
        return None
    return str(value).encode("utf-8")

def _coerce_value(q: SurveyQuestion, raw: Any) -> Tuple[dict, bytes]:
    """
    Coerce raw JSON value to the correct typed column.
    Returns (typed_fields_dict, encrypted_bytes_or_None).
    """
    # Sensitive path: always go to encrypted_value, do not store plaintext
    if q.sensitive:
        return ({}, _encrypt_if_needed(raw))

    t = q.type
    if t == QuestionType.TEXT:
        return ({"value_text": str(raw) if raw is not None else None}, None)

    if t == QuestionType.NUMBER:
        if raw in (None, ""):
            return ({"value_number": None}, None)
        try:
            return ({"value_number": Decimal(str(raw))}, None)
        except (InvalidOperation, ValueError):
            raise ValueError(f"Invalid number for question {q.code}")

    if t == QuestionType.DATE:
        if not raw:
            return ({"value_date": None}, None)
        # Expect ISO date
        try:
            return ({"value_date": date.fromisoformat(str(raw))}, None)
        except Exception:
            raise ValueError(f"Invalid date (YYYY-MM-DD) for question {q.code}")

    if t in (QuestionType.DROPDOWN, QuestionType.RADIO):
        # Single-select; store in value_text, but validate option existence
        val = str(raw) if raw is not None else None
        if val:
            if not SurveyQuestionOption.objects.filter(question=q, value=val).exists():
                raise ValueError(f"Invalid option '{val}' for question {q.code}")
        return ({"value_text": val}, None)

    if t == QuestionType.CHECKBOX:
        # Multi-select; expect list; validate each option
        if raw in (None, ""):
            return ({"value_json": []}, None)
        if not isinstance(raw, list):
            raise ValueError(f"Expected list for checkbox question {q.code}")
        for v in raw:
            if not SurveyQuestionOption.objects.filter(question=q, value=str(v)).exists():
                raise ValueError(f"Invalid option '{v}' for question {q.code}")
        return ({"value_json": [str(v) for v in raw]}, None)

    # default: store raw as JSON
    return ({"value_json": raw}, None)

def _validate_required(q: SurveyQuestion, answers_by_code: Dict[str, Any]):
    if q.required:
        if q.code not in answers_by_code or answers_by_code[q.code] in (None, "", []):
            raise ValueError(f"Missing required answer for {q.code}")

def _load_survey_index(survey: Survey):
    """
    Build helper indexes for fast code->question resolution.
    """
    sections = survey.sections.all().prefetch_related("questions__options")
    code_to_q = {}
    for sec in sections:
        for q in sec.questions.all():
            code_to_q[q.code] = q
    return code_to_q

@transaction.atomic
def submit_from_session(session_id: int, extra_answers: Dict[str, Any] | None = None) -> SurveyResponse:
    sess = get_object_or_404(SurveySession, pk=session_id)
    if sess.status == SessionStatus.ABANDONED:
        raise ValueError("Session abandoned")
    survey = sess.survey

    draft = dict(sess.partial_payload or {})
    if extra_answers:
        draft.update(extra_answers)

    if not draft:
        raise ValueError("No answers to submit")

    code_to_q = _load_survey_index(survey)

    # Required validation (basic; advanced conditional requirements can be added later)
    for q in code_to_q.values():
        _validate_required(q, draft)

    # Create response
    resp = SurveyResponse.objects.create(
        survey=survey,
        session=sess,
        invitation=sess.invitation,
        respondent_key=None,  # can be derived later if needed
        status="submitted",
    )

    # Optional: pick an active key for sensitive answers
    key = CryptoKey.objects.filter(active=True).order_by("id").first()

    # Write answers
    for code, raw in draft.items():
        q = code_to_q.get(code)
        if not q:
            # ignore unknown codes to keep submission robust
            continue
        typed, enc = _coerce_value(q, raw)
        ans = SurveyAnswer(response=resp, question=q, **typed)
        if enc is not None:
            ans.encrypted_value = enc
            if key:
                ans.key = key
        ans.save()

    # Mark session complete if not already
    if sess.status != SessionStatus.COMPLETED:
        sess.status = SessionStatus.COMPLETED
        sess.save()

    # Mark invitation complete
    if sess.invitation and sess.invitation.status != "completed":
        inv = sess.invitation
        inv.status = "completed"
        inv.save()

    return resp

@transaction.atomic
def submit_direct(survey_id: int, answers: Dict[str, Any], invitation_id: int | None = None, respondent_key: str | None = None) -> SurveyResponse:
    survey = get_object_or_404(Survey, pk=survey_id)
    if not answers:
        raise ValueError("No answers to submit")

    inv = None
    if invitation_id:
        inv = get_object_or_404(SurveyInvitation, pk=invitation_id, survey=survey)

    code_to_q = _load_survey_index(survey)
    for q in code_to_q.values():
        _validate_required(q, answers)

    resp = SurveyResponse.objects.create(
        survey=survey,
        session=None,
        invitation=inv,
        respondent_key=respondent_key,
        status="submitted",
    )

    key = CryptoKey.objects.filter(active=True).order_by("id").first()

    for code, raw in answers.items():
        q = code_to_q.get(code)
        if not q:
            continue
        typed, enc = _coerce_value(q, raw)
        ans = SurveyAnswer(response=resp, question=q, **typed)
        if enc is not None:
            ans.encrypted_value = enc
            if key:
                ans.key = key
        ans.save()

    if inv and inv.status != "completed":
        inv.status = "completed"
        inv.save()

    return resp
