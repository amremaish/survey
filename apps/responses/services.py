from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Tuple, Optional, Iterable, Mapping
import operator as _op
import re
import json
import hashlib
import base64

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404

from cryptography.fernet import Fernet

from apps.surveys.models import Survey, SurveyQuestion, QuestionType, SurveyInvitation, InvitationStatus
from apps.survey_sessions.models import SurveySession, SessionStatus
from .models import SurveyResponse, SurveyAnswer

# Supported comparison operators for show_if / required_if.
OPS: Mapping[str, callable] = {
    "=": _op.eq,
    "==": _op.eq,
    "!=": _op.ne,
    "<": _op.lt,
    "<=": _op.le,
    ">": _op.gt,
    ">=": _op.ge,
}


def _evaluate_condition(left: Any, op_symbol: str, right: Any) -> bool:
    """
    Safely evaluate a binary condition like `left < right`.
    Returns False if the operator is unsupported or if comparison fails.
    """
    func = OPS.get((op_symbol or "==").strip())
    if func is None:
        return False
    try:
        return func(left, right)
    except Exception:
        return False


# ---- Encryption utilities ------------------------------------------------------

def _derive_fernet(_alias: Optional[str]) -> Fernet:
    """
    Derive a Fernet key from RESPONSES_ENCRYPTION_SECRET (or SECRET_KEY fallback).

    Notes:
        - `_alias` is accepted for future multi-tenant / key-rotation routing; it is
          not currently used in the derivation, but kept for API stability.
    """
    secret = getattr(settings, "RESPONSES_ENCRYPTION_SECRET", None) or settings.SECRET_KEY or ""
    key_bytes = hashlib.sha256(str(secret).encode("utf-8")).digest()  # 32 bytes
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def _encrypt_value(raw: Any, alias: Optional[str]) -> Optional[bytes]:
    """
    Encrypt any JSON-serializable `raw` value. Returns None for None input.
    """
    if raw is None:
        return None
    f = _derive_fernet(alias)
    payload = json.dumps(raw, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return f.encrypt(payload)


def _decrypt_value(blob: Optional[bytes], alias: Optional[str]) -> Any:
    """
    Decrypt an encrypted `blob` produced by `_encrypt_value`.

    Back-compat:
        - If decryption fails, we attempt to treat `blob` as plaintext.
        - If plaintext is not JSON, return UTF-8 decoded string.
    """
    if blob is None:
        return None
    f = _derive_fernet(alias)
    try:
        plaintext = f.decrypt(blob)
    except Exception:
        # Legacy path: accept stored plaintext bytes
        try:
            plaintext = blob
        except Exception:
            return None
    try:
        return json.loads(plaintext.decode("utf-8", errors="ignore"))
    except Exception:
        try:
            return plaintext.decode("utf-8", errors="ignore")
        except Exception:
            return None


# ---- Indexing / lookups --------------------------------------------------------

class SurveyIndex:
    """
    Lightweight in-memory index for a Survey:
      - code_to_q:    question code -> SurveyQuestion
      - options_by_code: question code -> set of allowed option values (str)
    """

    def __init__(self, code_to_q: Dict[str, SurveyQuestion], options_by_code: Dict[str, set[str]]):
        self.code_to_q = code_to_q
        self.options_by_code = options_by_code

    @classmethod
    def build(cls, survey: Survey) -> "SurveyIndex":
        """
        Prefetch sections/questions/options once and prepare fast lookups.
        """
        sections = (
            survey.sections.all()
            .prefetch_related("questions__options")
        )
        code_to_q: Dict[str, SurveyQuestion] = {}
        options_by_code: Dict[str, set[str]] = {}

        for sec in sections:
            for q in sec.questions.all():
                code_to_q[q.code] = q
                if q.type in (QuestionType.DROPDOWN, QuestionType.RADIO, QuestionType.CHECKBOX):
                    options_by_code[q.code] = {str(opt.value) for opt in q.options.all()}
        return cls(code_to_q, options_by_code)


# ---- Validation ----------------------------------------------------------------

def _is_present(val: Any) -> bool:
    """Uniform presence check used by required/conditional validations."""
    return not (val in (None, "") or (isinstance(val, list) and len(val) == 0))


def _coerce_for_compare(ref_q: SurveyQuestion, raw: Any, target_raw: Any) -> tuple[Any, Any]:
    """
    Coerce `raw` (the value from answers) and `target_raw` (constraint value) to comparable types
    based on the referenced question's type. On error, returns (None, None) so comparisons fail-safe.
    """
    try:
        if ref_q.type == QuestionType.NUMBER:
            left = Decimal(str(raw)) if raw not in (None, "") else None
            right = Decimal(str(target_raw))
        elif ref_q.type == QuestionType.DATE:
            left = date.fromisoformat(str(raw)) if raw else None
            right = date.fromisoformat(str(target_raw))
        else:
            left = None if raw is None else str(raw)
            right = None if target_raw is None else str(target_raw)
        return left, right
    except Exception:
        return None, None


def _passes_visibility(q: SurveyQuestion, answers_by_code: Dict[str, Any], index: SurveyIndex) -> bool:
    """
    Returns True if the question is visible given its optional `show_if` constraint.
    If no `show_if`, visibility defaults to True.
    """
    constraints = q.constraints or {}
    if not isinstance(constraints, dict):
        return True

    sif = constraints.get("show_if")
    if not (sif and isinstance(sif, dict)):
        return True

    ref_code = sif.get("question_code")
    op_symbol = (sif.get("operator") or "==").strip()
    target_value = sif.get("value")

    if ref_code and ref_code in index.code_to_q:
        ref_q = index.code_to_q[ref_code]
        left_raw = answers_by_code.get(ref_code)
        left, right = _coerce_for_compare(ref_q, left_raw, target_value)
        if left is None or right is None:
            return False  # Unable to compare -> treat as not visible (conservative)
        return _evaluate_condition(left, op_symbol, right)

    # Unknown reference -> hide conservatively
    return False


def _validate_required_rules(q: SurveyQuestion, answers_by_code: Dict[str, Any], index: SurveyIndex) -> None:
    """
    Validate both unconditional `required` and conditional `required_if` for a single question.

    Visibility:
        - If `show_if` makes the question hidden, we skip required checks.
    """
    # If not visible, skip any required validation:
    if not _passes_visibility(q, answers_by_code, index):
        return

    # Unconditional required:
    if q.required and not _is_present(answers_by_code.get(q.code)):
        display = q.prompt or q.code or f"question #{q.id}"
        raise ValueError(f"Missing required answer for {display}")

    # Conditional required:
    constraints = q.constraints or {}
    if not isinstance(constraints, dict):
        return
    rif = constraints.get("required_if")
    if not (rif and isinstance(rif, dict)):
        return

    ref_code = rif.get("question_code")
    op_symbol = (rif.get("operator") or "==").strip()
    target_value = rif.get("value")

    if ref_code and ref_code in index.code_to_q:
        ref_q = index.code_to_q[ref_code]
        left_raw = answers_by_code.get(ref_code)
        left, right = _coerce_for_compare(ref_q, left_raw, target_value)
        cond = False if (left is None or right is None) else _evaluate_condition(left, op_symbol, right)
        if cond and not _is_present(answers_by_code.get(q.code)):
            display = q.prompt or q.code or f"question #{q.id}"
            raise ValueError(f"Missing required answer for {display} (conditional)")


def _validate_constraints(
    q: SurveyQuestion,
    raw: Any,
    answers_by_code: Dict[str, Any],
    index: SurveyIndex,
) -> None:
    """
    Validate the provided raw value against `q.constraints`.

    Implemented:
      - TEXT: min_length, max_length, pattern, error_message
      - NUMBER: min_value, max_value, step (w.r.t. min_value base)
      - DATE: min_date, max_date (YYYY-MM-DD)
      - DROPDOWN/RADIO: min_selected, max_selected (presence based, 0 or 1)
      - CHECKBOX: min_selected, max_selected (on list length)
      - Selection option validation for DROPDOWN/RADIO/CHECKBOX is done here using in-memory options.
    """
    constraints = q.constraints or {}
    if not isinstance(constraints, dict):
        constraints = {}

    t = q.type

    # Selection option validation using prefetched in-memory set:
    if t in (QuestionType.DROPDOWN, QuestionType.RADIO):
        if raw not in (None, ""):
            allowed = index.options_by_code.get(q.code, set())
            if str(raw) not in allowed:
                raise ValueError(f"Invalid option '{raw}' for question {q.code}")

    if t == QuestionType.CHECKBOX:
        if raw in (None, ""):
            vals: Iterable[str] = []
        elif isinstance(raw, list):
            vals = [str(v) for v in raw]
        else:
            raise ValueError(f"Expected list for checkbox question {q.code}")

        allowed = index.options_by_code.get(q.code, set())
        invalid = [v for v in vals if v not in allowed]
        if invalid:
            raise ValueError(f"Invalid option(s) {invalid} for question {q.code}")

    # TEXT constraints
    if t == QuestionType.TEXT:
        s = "" if raw is None else str(raw)
        min_len = constraints.get("min_length")
        max_len = constraints.get("max_length")
        if isinstance(min_len, (int, float)) and len(s) < int(min_len):
            raise ValueError(f"{q.code}: must be at least {int(min_len)} characters")
        if isinstance(max_len, (int, float)) and len(s) > int(max_len):
            raise ValueError(f"{q.code}: must be at most {int(max_len)} characters")
        pattern = constraints.get("pattern")
        if pattern:
            try:
                if not re.fullmatch(str(pattern), s or ""):
                    msg = constraints.get("error_message") or f"{q.code}: value does not match pattern"
                    raise ValueError(msg)
            except re.error:
                # Ignore invalid regex patterns silently
                pass

    # NUMBER constraints
    if t == QuestionType.NUMBER and raw not in (None, ""):
        try:
            num = Decimal(str(raw))
        except Exception:
            # Coercion error will be raised during storage coercion
            num = None
        if num is not None:
            min_v = constraints.get("min_value")
            max_v = constraints.get("max_value")
            if min_v is not None:
                try:
                    if num < Decimal(str(min_v)):
                        raise ValueError(f"{q.code}: must be >= {min_v}")
                except Exception:
                    pass
            if max_v is not None:
                try:
                    if num > Decimal(str(max_v)):
                        raise ValueError(f"{q.code}: must be <= {max_v}")
                except Exception:
                    pass
            step = constraints.get("step")
            if step not in (None, 0, 0.0, "0"):
                try:
                    step_d = Decimal(str(step))
                    base = Decimal(str(constraints.get("min_value", 0)))
                    remainder = (num - base) % step_d
                    if remainder != 0:
                        raise ValueError(f"{q.code}: must be in increments of {step}")
                except Exception:
                    pass

    # DATE constraints
    if t == QuestionType.DATE and raw not in (None, ""):
        try:
            d = date.fromisoformat(str(raw))
        except Exception:
            d = None
        if d is not None:
            min_d = constraints.get("min_date")
            max_d = constraints.get("max_date")
            if min_d:
                try:
                    if d < date.fromisoformat(str(min_d)):
                        raise ValueError(f"{q.code}: date must be on/after {min_d}")
                except Exception:
                    pass
            if max_d:
                try:
                    if d > date.fromisoformat(str(max_d)):
                        raise ValueError(f"{q.code}: date must be on/before {max_d}")
                except Exception:
                    pass

    # Selection count constraints
    if t in (QuestionType.DROPDOWN, QuestionType.RADIO):
        count = 1 if (raw not in (None, "")) else 0
        min_sel = constraints.get("min_selected")
        max_sel = constraints.get("max_selected")
        if isinstance(min_sel, (int, float)) and count < int(min_sel):
            raise ValueError(f"{q.code}: at least {int(min_sel)} selection required")
        if isinstance(max_sel, (int, float)) and count > int(max_sel):
            raise ValueError(f"{q.code}: at most {int(max_sel)} selection allowed")

    if t == QuestionType.CHECKBOX:
        count = len(raw) if isinstance(raw, list) else 0
        min_sel = constraints.get("min_selected")
        max_sel = constraints.get("max_selected")
        if isinstance(min_sel, (int, float)) and count < int(min_sel):
            raise ValueError(f"{q.code}: select at least {int(min_sel)} option(s)")
        if isinstance(max_sel, (int, float)) and count > int(max_sel):
            raise ValueError(f"{q.code}: select at most {int(max_sel)} option(s)")


# ---- Coercion to storage fields ------------------------------------------------

def _coerce_to_storage(q: SurveyQuestion, raw: Any) -> Tuple[Dict[str, Any], Optional[Any]]:
    """
    Convert a raw JSON answer to the appropriate storage field(s) for SurveyAnswer.

    Returns:
        (typed_fields, sensitive_payload_or_None)

    Rules:
        - If q.sensitive: do not store in plaintext; return raw to be encrypted (encrypted_value).
        - TEXT:        -> value_text (str or None)
        - NUMBER:      -> value_number (Decimal or None)
        - DATE:        -> value_date (date or None)
        - DROPDOWN/RADIO: single-select stored in value_text (validated earlier)
        - CHECKBOX:    multi-select stored as comma-separated string in value_text
                        (schema-preserving alternative would be a JSON field if available)
        - Default:     stringify into value_text
    """
    if q.sensitive:
        return ({}, raw)

    t = q.type

    if t == QuestionType.TEXT:
        return ({"value_text": None if raw is None else str(raw)}, None)

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
        try:
            return ({"value_date": date.fromisoformat(str(raw))}, None)
        except Exception:
            raise ValueError(f"Invalid date (YYYY-MM-DD) for question {q.code}")

    if t in (QuestionType.DROPDOWN, QuestionType.RADIO):
        val = str(raw) if raw is not None else None
        return ({"value_text": val}, None)

    if t == QuestionType.CHECKBOX:
        if raw in (None, ""):
            return ({"value_text": None}, None)
        if not isinstance(raw, list):
            raise ValueError(f"Expected list for checkbox question {q.code}")
        return ({"value_text": ",".join([str(v) for v in raw])}, None)

    return ({"value_text": None if raw is None else str(raw)}, None)


# ---- Core submission flow ------------------------------------------------------

def _prepare_answer_models(
    response: SurveyResponse,
    answers_by_code: Dict[str, Any],
    index: SurveyIndex,
    encryption_alias: Optional[str],
) -> list[SurveyAnswer]:
    """
    Validate & coerce all answers, returning a list of SurveyAnswer instances ready to be saved.

    Steps:
        1) Per-question required / conditional checks.
        2) Per-answer constraints validation.
        3) Coercion to storage fields + optional encryption.
    """
    # 1) Required validations (including visibility and required_if):
    for q in index.code_to_q.values():
        _validate_required_rules(q, answers_by_code, index)

    # 2) Build SurveyAnswer models (validating constraints + coercion per answer):
    models: list[SurveyAnswer] = []
    for code, raw in answers_by_code.items():
        q = index.code_to_q.get(code)
        if not q:
            # Ignore unknown codes to keep submission robust:
            continue

        # Per-answer constraints:
        _validate_constraints(q, raw, answers_by_code, index)

        # Coerce to storage fields:
        typed, sensitive_raw = _coerce_to_storage(q, raw)
        ans = SurveyAnswer(response=response, question=q, **typed)

        # Encrypt for sensitive questions:
        if sensitive_raw is not None:
            ans.encrypted_value = _encrypt_value(sensitive_raw, encryption_alias)

        models.append(ans)

    return models


@transaction.atomic
def _submit(
    survey: Survey,
    answers_by_code: Dict[str, Any],
    session: Optional[SurveySession] = None,
    encryption_alias: Optional[str] = None,
) -> SurveyResponse:
    """
    Internal submit function shared by both public entry points.

    Creates a SurveyResponse, validates + persists answers (bulk_create),
    and marks the session complete if applicable.
    """
    if not answers_by_code:
        raise ValueError("No answers to submit")

    index = SurveyIndex.build(survey)

    if session and getattr(session, 'invitation_token', None):
        try:
            inv = SurveyInvitation.objects.filter(token=session.invitation_token, survey=survey).first()
            from django.utils import timezone
            if inv and inv.expires_at and inv.expires_at < timezone.now():
                raise ValueError("This invitation has expired")
            if inv and inv.status == InvitationStatus.SUBMITTED:
                raise ValueError("You have already submitted this survey")
        except ValueError:
            raise
        except Exception:
            pass

    response = SurveyResponse.objects.create(
        survey=survey,
        session=session,
        respondent_email=(getattr(session, 'invited_email', None) if session else None),
        status="submitted",
    )

    answers = _prepare_answer_models(response, answers_by_code, index, encryption_alias)
    if not answers:
        # It's possible all provided codes were unknown; treat as invalid submit:
        raise ValueError("No valid answers to submit")

    SurveyAnswer.objects.bulk_create(answers)

    # If this response is tied to an invitation, mark it as submitted
    if session and getattr(session, 'invitation_token', None):
        try:
            inv = SurveyInvitation.objects.filter(token=session.invitation_token, survey=survey).first()
            if inv and inv.status != InvitationStatus.SUBMITTED:
                inv.status = InvitationStatus.SUBMITTED
                inv.response_id = response.id
                inv.save(update_fields=["status", "response_id", "updated_at"])
        except Exception:
            # Do not block submission on invitation update errors
            pass

    if session and session.status != SessionStatus.COMPLETED:
        session.status = SessionStatus.COMPLETED
        session.save(update_fields=["status"])

    return response


# ---- Public API ---------------------------------------------------------------

@transaction.atomic
def submit_from_session(
    session_id: int,
    extra_answers: Optional[Dict[str, Any]] = None,
    *,
    encryption_alias: Optional[str] = None,
) -> SurveyResponse:
    """
    Submit a survey using an existing SurveySession.

    Flow:
        - Load session and its survey.
        - Merge session.partial_payload with `extra_answers` (extra overrides).
        - Validate show_if / required / required_if and constraints.
        - Coerce & (optionally) encrypt sensitive values.
        - Persist via bulk_create; mark session COMPLETED.

    Raises:
        - ValueError if session is ABANDONED or no answers to submit.
        - ValueError for validation/coercion errors (with human-friendly messages).
    """
    sess = get_object_or_404(SurveySession, pk=session_id)
    if sess.status == SessionStatus.ABANDONED:
        raise ValueError("Session abandoned")

    survey = sess.survey
    draft = dict(sess.partial_payload or {})
    if extra_answers:
        draft.update(extra_answers)

    return _submit(
        survey=survey,
        answers_by_code=draft,
        session=sess,
        encryption_alias=encryption_alias,
    )


@transaction.atomic
def submit_direct(
    survey_id: int,
    answers: Dict[str, Any],
    *,
    encryption_alias: Optional[str] = None,
) -> SurveyResponse:
    """
    Submit a survey directly without (or before) using a SurveySession.

    Notes:
        - For convenience, we attempt to attach the most recent session for this survey if one exists.
        - Validation & persistence are identical to `submit_from_session`.

    Raises:
        - ValueError for empty answers or validation/coercion problems.
    """
    survey = get_object_or_404(Survey, pk=survey_id)
    sess = SurveySession.objects.filter(survey=survey).order_by("-id").first()
    return _submit(
        survey=survey,
        answers_by_code=answers,
        session=sess,
        encryption_alias=encryption_alias,
    )