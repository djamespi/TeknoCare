from django import forms

from .models import UserSettings


class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = UserSettings
        fields = ("dark_mode", "email_notifications")
        labels = {"dark_mode": "Use dark mode", "email_notifications": "Email notifications (preference only)"}
        help_texts = {
            "dark_mode": "Applies to your signed-in clinic pages after saving, including on your next sign-in.",
            "email_notifications": "Email delivery is not configured. No notifications will be sent, even when this preference is selected.",
        }
