"""Aggregate clinic source rows using their own dates and current statuses."""
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Lower, Trim

from apps.appointments.models import Appointment
from apps.billing.models import StudentCharge
from apps.clinical.models import MedicalRecord, Referral
from apps.patients.models import Affiliation
from apps.register.models import User


ASSESSMENT_IDENTITIES = (
    ("JOIN-DEMO-001", "ana@join-demo.example.invalid"),
    ("JOIN-DEMO-002", "ben@join-demo.example.invalid"),
    ("JOIN-DEMO-003", "carlo@join-demo.example.invalid"),
    ("JOIN-DEMO-004", "maya@join-demo.example.invalid"),
)


def filter_dates(rows, field, filters):
    if start := filters.get("from_date"):
        rows = rows.filter(**{f"{field}__date__gte": start})
    if end := filters.get("through_date"):
        rows = rows.filter(**{f"{field}__date__lte": end})
    return rows


def _assessment_accounts():
    # Match the original reserved pairs, including legacy whitespace in identities.
    pairs = Q()
    for school_id, email in ASSESSMENT_IDENTITIES:
        pairs |= Q(fixture_id=school_id, fixture_email=email)
    return User.objects.alias(fixture_id=Trim("school_id"), fixture_email=Lower(Trim("email"))).filter(pairs).values("pk")


def _counts(rows, field, choices):
    counts = {
        row[field]: row["count"]
        for row in rows.order_by().values(field).annotate(count=Count("pk"))
    }
    return [(label, counts.get(value, 0)) for value, label in choices]


def reportable_appointments():
    fixtures = _assessment_accounts()
    return Appointment.objects.exclude(
        Q(patient_id__in=fixtures) | Q(slot__provider_id__in=fixtures),
    )


def operational_report(filters):
    fixtures = _assessment_accounts()
    clinic_visits = MedicalRecord.objects.exclude(
        Q(patient_id__in=fixtures) | Q(provider_id__in=fixtures) | Q(appointment__slot__provider_id__in=fixtures),
    )
    clinic_referrals = Referral.objects.filter(record_id__in=clinic_visits.values("pk")).exclude(
        referred_by_provider_id__in=fixtures,
    )
    clinic_charges = StudentCharge.objects.filter(record_id__in=clinic_visits.values("pk"))
    if term := filters["term"]:
        clinic_charges = clinic_charges.filter(term=term)

    appointments = filter_dates(reportable_appointments(), "slot__start_time", filters)
    visits = filter_dates(clinic_visits, "visited_at", filters)
    referrals = filter_dates(clinic_referrals, "referred_at", filters)
    charges = filter_dates(clinic_charges, "created_at", filters)

    workload = visits.values(
        "provider_id", first_name=F("provider__provider__fname"), last_name=F("provider__provider__lname"),
        university_id=F("provider__provider__school_id"),
    ).annotate(
        total=Count("pk"),
        draft=Count("pk", filter=Q(status=MedicalRecord.Status.DRAFT)),
        finalized=Count("pk", filter=Q(status=MedicalRecord.Status.FINALIZED)),
    ).order_by("last_name", "first_name", "provider_id")

    charge_totals = charges.values(
        "term_id", "currency_code", academic_year=F("term__academic_year"), semester=F("term__semester"),
    ).annotate(
        lines=Count("pk"),
        pending=Sum("amount", filter=Q(status=StudentCharge.Status.PENDING), default=0),
        posted=Sum("amount", filter=Q(status=StudentCharge.Status.POSTED), default=0),
        voided=Sum("amount", filter=Q(status=StudentCharge.Status.VOIDED), default=0),
    ).order_by("-academic_year", "semester", "term_id", "currency_code")

    return {
        "appointment_counts": _counts(appointments, "status", Appointment.Status.choices),
        "visit_counts": _counts(visits, "status", MedicalRecord.Status.choices),
        "affiliation_counts": _counts(visits, "affiliation_at_visit", [*Affiliation.choices, (None, "Unverified")]),
        "referral_counts": _counts(referrals, "status", Referral.Status.choices),
        "workload": workload,
        "charge_totals": charge_totals,
    }
