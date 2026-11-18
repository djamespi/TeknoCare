from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.common.web import ReferenceFilterForm, add_form_errors, clinic_admin_required
from apps.register.services import create_provider_account
from .forms import ProviderAccountForm, ProviderAttachForm, ProviderForm
from .models import Provider
from .services import attach_provider_profile, save_provider


@clinic_admin_required
@require_http_methods(["GET"])
def provider_list(request):
    form = ReferenceFilterForm(request.GET)
    form.fields["state"].label = "Clinical activation"
    providers = Provider.objects.select_related("provider").order_by("provider__school_id", "pk")
    if form.is_valid():
        query = form.cleaned_data["q"]
        providers = providers.filter(Q(provider__school_id__icontains=query) | Q(provider__fname__icontains=query) | Q(provider__lname__icontains=query) | Q(provider_type__icontains=query))
        if form.cleaned_data["state"]:
            providers = providers.filter(is_active=form.cleaned_data["state"] == "active")
    else:
        providers = providers.none()
    return render(request, "providers/provider_list.html", {"filter_form": form,
        "page_obj": Paginator(providers, 10).get_page(request.GET.get("page"))})


@clinic_admin_required
@require_http_methods(["GET", "POST"])
def provider_create(request):
    form = ProviderAccountForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            user = create_provider_account(actor=request.user, **form.account_values(), provider_type=form.cleaned_data["provider_type"],
                license_number=form.cleaned_data["license_number"], specialization=form.cleaned_data["specialization"] or None)
        except ValidationError as error:
            add_form_errors(form, error)
        except IntegrityError:
            form.add_error(None, "That ID, email or license was just used. Review existing accounts before retrying.")
        else:
            messages.success(request, "Provider account created, clinically inactive. Share credentials privately; no email or forced password-change flag exists. Review before activation.")
            return redirect("providers:provider_edit", pk=user.pk)
    return render(request, "includes/management_form.html", {"form": form, "title": "Add provider account",
        "description": "Creates a new login and inactive Provider profile, not a Patient profile. Use supplied or fictional identity/credentials; enrollment and professional credentials are not verified automatically.", "back_url": "providers:provider_list"})


@clinic_admin_required
@require_http_methods(["GET", "POST"])
def provider_attach(request):
    form = ProviderAttachForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            provider = attach_provider_profile(actor=request.user, user_id=form.cleaned_data["user"].pk)
        except ValidationError as error:
            add_form_errors(form, error)
        except IntegrityError:
            form.add_error(None, "A profile was just attached to that account. Refresh and review the provider list.")
        else:
            messages.success(request, "Inactive, Unverified Provider profile attached. The account role and existing Patient profile are unchanged.")
            return redirect("providers:provider_edit", pk=provider.pk)
    return render(request, "includes/management_form.html", {"form": form, "title": "Attach existing provider account",
        "description": "For an Admin who also practices or an existing Provider missing its profile. This does not grant clinical powers until designation and activation are reviewed.", "back_url": "providers:provider_list"})


@clinic_admin_required
@require_http_methods(["GET", "POST"])
def provider_edit(request, pk):
    provider = get_object_or_404(Provider.objects.select_related("provider"), pk=pk)
    form = ProviderForm(request.POST if request.method == "POST" else None, instance=provider)
    if request.method == "POST" and form.is_valid():
        try:
            save_provider(actor=request.user, provider_id=pk, **form.cleaned_data)
        except ValidationError as error:
            add_form_errors(form, error)
        except IntegrityError:
            form.add_error(None, "That license was saved concurrently. Review the provider details and try again.")
        else:
            messages.success(request, "Provider profile saved. Historical visits were preserved. Activation does not restore disabled slots.")
            return redirect("providers:provider_list")
    return render(request, "providers/provider_form.html", {"form": form, "provider_account": provider.provider})
