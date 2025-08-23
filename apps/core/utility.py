from __future__ import annotations

from typing import Optional, Tuple, Type

from django.utils.text import slugify


def parse_int(value: object, default: int) -> int:
    """Safe int parse with default fallback."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def page_bounds(page: int, page_size: int) -> Tuple[int, int]:
    """Compute start/end slice indices, guarding lower bounds and capping size."""
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    start = (page - 1) * page_size
    end = start + page_size
    return start, end


def unique_slug_for_code(model: Type, base: str, code_field: str = "code") -> str:
    """Generate a unique, URL-safe code using base and numeric suffix if needed."""
    base = slugify(base) or "survey"
    candidate = base
    i = 1
    exists = model.objects.filter(**{code_field: candidate}).exists()
    while exists:
        i += 1
        candidate = f"{base}-{i}"
        exists = model.objects.filter(**{code_field: candidate}).exists()
    return candidate


def sort_order_conflict_exists(section, sort_order: Optional[int], exclude_pk: Optional[int] = None) -> bool:
    """
    Check if a given sort_order already exists within the section.
    Import locally to avoid circulars with apps.surveys.
    """
    if sort_order is None:
        return False
    from apps.surveys.models import SurveyQuestion  # local import
    qs = SurveyQuestion.objects.only("id").filter(section=section, sort_order=sort_order)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs.exists()


