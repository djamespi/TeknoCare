from urllib.parse import urlsplit

from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from apps.audit.models import AuditLog
from apps.common.permissions import require_permission
from apps.portal.entrypoint import portal_ready
from apps.register.services import change_password, reset_account_password
from .forms import AdminPasswordResetForm, LoginForm, PasswordChangeForm


def _return_url(request):
    target = request.POST.get("next", request.GET.get("next", ""))
    if url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        if urlsplit(target).path not in {reverse("login:login"), reverse("register:register"), reverse("logout")}:
            return target
    return reverse("home:home")


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect(_return_url(request))
    if request.method == "GET" and request.GET.get("next", "") in {"", reverse("home:home")} and portal_ready():
        return redirect("portal:index")

    form = LoginForm(request.POST if request.method == "POST" else None, request=request)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            login(request, form.user)
            AuditLog.objects.create(actor_user=form.user, action_performed="Account signed in", target_table="user", target_record_id=form.user.pk)
        return redirect(_return_url(request))
    return render(request, "login/login.html", {"form": form, "next": request.POST.get("next", request.GET.get("next", ""))})


def _form_errors(form, error):
    if hasattr(error, "message_dict"):
        for field, errors in error.message_dict.items():
            form.add_error(field if field in form.fields else None, errors)
    else:
        form.add_error(None, error)


@login_required
@require_http_methods(["GET", "POST"])
def password_change_view(request):
    form = PasswordChangeForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            user = change_password(actor=request.user, old_password=form.cleaned_data["old_password"], new_password=form.cleaned_data["new_password1"])
        except ValidationError as error:
            _form_errors(form, error)
        else:
            update_session_auth_hash(request, user)
            messages.success(request, "Your password was changed. Other existing sessions must sign in again.")
            return redirect("login:password_change")
    return render(request, "login/password_change.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def admin_password_reset_view(request):
    require_permission(request.user, "accounts.manage")
    form = AdminPasswordResetForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            reset_account_password(actor=request.user, school_id=form.cleaned_data["university_id"],
                admin_password=form.cleaned_data["admin_password"], new_password=form.cleaned_data["new_password1"])
        except ValidationError as error:
            _form_errors(form, error)
        else:
            messages.success(request, "The account password was reset. Its role and status are unchanged. No email was sent.")
            return redirect("login:admin_password_reset")
    return render(request, "login/admin_password_reset.html", {"form": form})
