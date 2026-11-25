from django import template
from django.http import QueryDict
from django.urls import reverse

from apps.common.permissions import clinical_provider

register = template.Library()


@register.simple_tag(takes_context=True)
def pagination_url(context, page_number, page_param="page"):
    request = context.get("request")
    query = request.GET.copy() if request else QueryDict(mutable=True)
    query[page_param] = str(page_number)
    return f"?{query.urlencode()}"


@register.inclusion_tag("includes/navigation.html", takes_context=True)
def clinic_navigation(context):
    request = context["request"]
    user = request.user
    has_patient = hasattr(user, "patient_profile")
    clinician = clinical_provider(user)
    groups = [("Workspace", [("home:home", "Overview", "home")])]
    operations = []
    if user.is_staff or clinician:
        operations.append(("reception:queue", "Reception queue", "people"))
    if clinician:
        operations.extend([
            ("consultation:list", "Clinical encounters", "pulse"),
            ("patients:allergy_lookup", "Allergy review", "record"),
            ("prescriptions:formulary", "Formulary", "pill"),
        ])
    if user.is_staff or clinician:
        operations.append(("availability:list", "Availability", "calendar"))
    if user.is_staff:
        operations.append(("patient_intake:list", "Patient intake", "person"))
    if operations:
        groups.append(("Clinic work", operations))
    if user.is_staff:
        groups.append(("Administration", [
            ("university:management", "Clinic setup", "clinic"),
            ("billing:charges", "Tuition charges", "receipt"),
            ("audit:reports", "Operational reports", "chart"),
            ("audit:history", "Audit history", "clock"),
        ]))
    if has_patient:
        groups.append(("My care", [
            ("booking:browse", "Book a visit", "calendar"),
            ("booking:list", "My appointments", "calendar"),
            ("patients:visits", "My visit summaries", "record"),
            ("prescriptions:history", "My prescriptions", "pill"),
            ("billing:patient_charges", "My tuition charges", "receipt"),
            ("patients:details", "Patient details", "person"),
        ]))

    current = request.path
    # The prescription catalog and clinical workspace share a URL prefix
    # with personal prescription history, but belong to different menus.
    route = request.resolver_match.view_name if request.resolver_match else ""
    if route.startswith(("consultation:diagnosis", "prescriptions:medication", "prescriptions:catalog")):
        section = "university:management"
    elif route.startswith("prescriptions:") and route not in {"prescriptions:history", "prescriptions:print", "prescriptions:formulary"}:
        section = "consultation:list"
    elif route.startswith("home:"):
        section = "home:home"
    else:
        sections = [(reverse(name), name) for _, links in groups for name, _, _ in links if name != "home:home"]
        section = max((item for item in sections if current.startswith(item[0])), default=("", ""))[1]
    primary = [("home:home", "Home")]
    if user.is_staff:
        primary.extend([("reception:queue", "Reception"), ("patient_intake:list", "People"), ("billing:charges", "Charges"), ("university:management", "Clinic setup")])
    elif clinician:
        primary.extend([("consultation:list", "Encounters"), ("availability:list", "Schedule"), ("prescriptions:formulary", "Formulary")])
    elif has_patient:
        primary.extend([("booking:browse", "Book a visit"), ("booking:list", "Appointments"), ("patients:visits", "Records"), ("patients:details", "Health profile")])
    return {"groups": groups, "primary": primary, "current": current, "section": section}
