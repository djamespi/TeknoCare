from django import forms

from .models import Profile


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("phone_number", "home_address", "bio")
        widgets = {"bio": forms.Textarea(attrs={"rows": 5})}
