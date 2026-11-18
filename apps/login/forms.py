from django import forms
from django.contrib.auth import authenticate


class LoginForm(forms.Form):
    university_id = forms.CharField(label="University ID", max_length=20,
        widget=forms.TextInput(attrs={"id": "university_id", "autocomplete": "username"}))
    password = forms.CharField(strip=False, widget=forms.PasswordInput(attrs={"id": "password", "autocomplete": "current-password"}))

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.user = None

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("university_id") and cleaned.get("password"):
            self.user = authenticate(self.request, username=cleaned["university_id"], password=cleaned["password"])
            if self.user is None:
                raise forms.ValidationError("Invalid University ID or password. Contact the clinic administrator if your access changed.")
        return cleaned


class PasswordChangeForm(forms.Form):
    old_password = forms.CharField(label="Current password", strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))
    new_password1 = forms.CharField(label="New password", strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    new_password2 = forms.CharField(label="Confirm new password", strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("new_password1") != cleaned.get("new_password2"):
            self.add_error("new_password2", "Passwords do not match.")
        return cleaned


class AdminPasswordResetForm(PasswordChangeForm):
    old_password = None
    university_id = forms.CharField(label="Account University ID", max_length=20)
    admin_password = forms.CharField(label="Your administrator password", strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))
    field_order = ["university_id", "admin_password", "new_password1", "new_password2"]
