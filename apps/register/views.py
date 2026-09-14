from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import RegistrationForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect("home:home")

    form = RegistrationForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Your TeknoCare account has been created. You can now sign in.")
        return redirect("login:login")
    return render(request, "register/register.html", {"form": form})
