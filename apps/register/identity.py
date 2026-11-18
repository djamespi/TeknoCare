"""Identity normalization without assuming a university ID format or email domain."""
from django.db.models.functions import Lower, Trim


def normalize_school_id(value):
    return (value or "").strip()


def normalize_email(value):
    return (value or "").strip().lower()


def identity_matches(queryset, *, school_id=None, email=None):
    if school_id is not None:
        return queryset.annotate(identity_value=Trim("school_id")).filter(identity_value=normalize_school_id(school_id))
    return queryset.annotate(identity_value=Lower(Trim("email"))).filter(identity_value=normalize_email(email))
