from django import forms

from .models import Profile


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("full_name", "age", "home_address", "bio")
        widgets = {"bio": forms.Textarea(attrs={"rows": 5})}
