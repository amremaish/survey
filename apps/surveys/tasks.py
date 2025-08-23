from __future__ import annotations

import logging
import smtplib
from typing import List

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.db import transaction

from survey.celery import celery_app  # <-- important: from survey.celery
from apps.surveys.models import Survey, SurveyInvitation, InvitationStatus

logger = logging.getLogger(__name__)


def _parse_expires_at(expires_at_iso: str) -> timezone.datetime:
    """
    Robustly parse ISO8601 with 'Z' or offsets. If naive, assume UTC.
    """
    if not expires_at_iso:
        raise ValueError("expires_at_iso is required")
    s = expires_at_iso.replace("Z", "+00:00")
    dt = parse_datetime(s)
    if dt is None:
        # Fallback: strict fromisoformat may still work for some shapes
        dt = timezone.datetime.fromisoformat(s)
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.utc)
    return dt


@celery_app.task(
    bind=True,
    # Retry only on SMTP/network issues (broad but avoid retrying on bad addresses)
    autoretry_for=(smtplib.SMTPException, smtplib.SMTPServerDisconnected, ConnectionError, TimeoutError),
    retry_backoff=10,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
    acks_late=True,
)
def send_invitation_email_task(self, emails: List[str], links: List[str], survey_title: str) -> int:
    """
    Send invitation emails (1:1 email->link). Expects equal-length lists.
    Uses a single SMTP connection for the whole batch.
    """
    if len(emails) != len(links):
        raise ValueError(f"emails/links length mismatch: {len(emails)} != {len(links)}")

    subject = f"You're invited to take: {survey_title}"
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")

    messages: list[EmailMultiAlternatives] = []
    for to, invite_url in zip(emails, links):
        html_body = render_to_string(
            "emails/invitation.html",
            {"survey_title": survey_title, "invite_url": invite_url, "site_url": site_url},
        )
        msg = EmailMultiAlternatives(
            subject=subject,
            body=f"Please open {invite_url}",
            from_email=from_email,
            to=[to],
        )
        msg.attach_alternative(html_body, "text/html")
        messages.append(msg)

    # Send all messages over one connection
    try:
        with get_connection(fail_silently=False) as conn:
            sent = conn.send_messages(messages) or 0
        logger.info("Invitation batch sent", extra={"sent": sent, "batch_size": len(emails)})
        return int(sent)
    except Exception as exc:
        logger.exception(
            "Failed to send invitation batch. Host=%s Port=%s TLS=%s SSL=%s From=%s",
            getattr(settings, "EMAIL_HOST", None),
            getattr(settings, "EMAIL_PORT", None),
            getattr(settings, "EMAIL_USE_TLS", None),
            getattr(settings, "EMAIL_USE_SSL", None),
            from_email,
        )
        raise


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),  # creation is idempotent if you enforce uniqueness on (survey,email,token)
    retry_backoff=5,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
    acks_late=True,
)
def create_invitations_task(self, survey_id: int, emails: List[str], expires_at_iso: str) -> dict:
    """
    Create SurveyInvitation rows in batches and queue email sending per batch.

    - Validates survey exists
    - Chunks emails by 200, bulk-creates invitations per chunk
    - For each chunk, enqueues send_invitation_email_task with that email list
    Returns {"created": total_created}
    """
    BATCH = 200
    survey = Survey.objects.select_related("organization").get(pk=survey_id)
    expires_at = _parse_expires_at(expires_at_iso)

    base = getattr(settings, "SITE_URL", "http://localhost:8000").rstrip("/")
    total_created = 0

    from django.utils.crypto import get_random_string

    for i in range(0, len(emails), BATCH):
        chunk = emails[i : i + BATCH]
        tokens = []
        objects = []
        for email in chunk:
            token = get_random_string(48)
            tokens.append(token)
            objects.append(
                SurveyInvitation(
                    organization=survey.organization,
                    survey=survey,
                    email=email,
                    token=token,
                    expires_at=expires_at,
                    status=InvitationStatus.PENDING,
                )
            )

        with transaction.atomic():
            # If you add unique=True to token, collisions will raise; extremely unlikely with 48 chars, but good to enforce.
            SurveyInvitation.objects.bulk_create(objects, batch_size=BATCH, ignore_conflicts=False)

        total_created += len(objects)
        links = [f"{base}/survey/{survey.code}?token={tok}" for tok in tokens]

        # Enqueue email sending for this chunk
        send_invitation_email_task.delay(chunk, links, survey.title)

    logger.info("Invitations created", extra={"survey_id": survey_id, "count": total_created})
    return {"created": total_created}


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=10,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
    acks_late=True,
)
def mark_expired_invitations_task(self, batch_size: int = 200) -> int:
    """
    Mark pending invitations as expired in batches.
    Scans SurveyInvitation where status=PENDING and expires_at < now,
    updates them in chunks of `batch_size`. Returns total updated.
    """
    now = timezone.now()
    total = 0
    while True:
        ids = list(
            SurveyInvitation.objects.filter(
                status=InvitationStatus.PENDING,
                expires_at__lt=now,
            )
            .order_by("id")
            .values_list("id", flat=True)[:batch_size]
        )
        if not ids:
            break

        updated = SurveyInvitation.objects.filter(id__in=ids).update(
            status=InvitationStatus.EXPIRED,
            updated_at=now,
        )
        total += updated
        if updated < batch_size:
            break

    logger.info("Expired invitations marked", extra={"count": total})
    return total
