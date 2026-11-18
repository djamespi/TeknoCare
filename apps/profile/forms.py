from django import forms

from .models import Profile


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("phone_number", "home_address", "bio")
        labels = {"phone_number": "Contact phone", "home_address": "Home address", "bio": "About you (optional)"}
        help_texts = {"bio": "A short non-clinical note. Do not put sensitive health information here."}
        widgets = {
            "phone_number": forms.TextInput(attrs={"type": "tel", "autocomplete": "tel"}),
            "home_address": forms.Textarea(attrs={"rows": 3, "autocomplete": "street-address"}),
            "bio": forms.Textarea(attrs={"rows": 4}),
        }
