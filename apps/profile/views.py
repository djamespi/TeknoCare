from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.patients.models import Patient

from .forms import ProfileForm
from .models import Profile


@login_required
@require_http_methods(["GET", "POST"])
def profile_view(request):
    profile = Profile.objects.filter(user=request.user).first() or Profile(user=request.user)
    form = ProfileForm(request.POST if request.method == "POST" else None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile has been saved.")
        return redirect("profile:profile")
    return render(request, "profile/profile.html", {
        "form": form, "has_patient_profile": Patient.objects.filter(pk=request.user.pk).exists(),
    })
