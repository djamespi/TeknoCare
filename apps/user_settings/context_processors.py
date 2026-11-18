from .models import UserSettings


def appearance(request):
    dark_mode = False
    if request.user.is_authenticated:
        dark_mode = UserSettings.objects.filter(user_id=request.user.pk).values_list("dark_mode", flat=True).first()
    return {"clinic_theme": "dark" if dark_mode else "light"}
