from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import UserSettingsForm
from .models import UserSettings


@login_required
def settings_view(request):
    settings, _ = UserSettings.objects.get_or_create(user=request.user)
    form = UserSettingsForm(request.POST or None, instance=settings)
    if form.is_valid():
        form.save()
        return redirect("user_settings:settings")
    return render(request, "user_settings/settings.html", {"form": form})
