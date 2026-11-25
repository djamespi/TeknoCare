from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.portal.entrypoint import portal_ready

from .forms import RegistrationForm


@require_http_methods(["GET", "POST"])
def register_view(request):
    if request.user.is_authenticated:
        return redirect("home:home")
    if request.method == "GET" and portal_ready():
        return redirect(reverse("portal:index") + "#/register")

    form = RegistrationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            form.save()
        except IntegrityError:
            form.add_error(None, "That University ID or email was just registered. Check your details or sign in.")
        except ValidationError as error:
            form.add_error(None, " ".join(error.messages))
        else:
            messages.success(request, "Your prototype Student account has been created. You can now sign in.")
            return redirect("login:login")
    return render(request, "register/register.html", {"form": form})
