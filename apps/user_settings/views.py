from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import UserSettingsForm
from .models import UserSettings


@login_required
@require_http_methods(["GET", "POST"])
def settings_view(request):
    settings = UserSettings.objects.filter(user=request.user).first() or UserSettings(user=request.user)
    form = UserSettingsForm(request.POST if request.method == "POST" else None, instance=settings)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your preferences have been saved. Email delivery is not available.")
        return redirect("user_settings:settings")
    return render(request, "user_settings/settings.html", {"form": form})
