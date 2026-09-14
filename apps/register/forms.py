from django import forms
from django.contrib.auth.models import User

from apps.profile.models import Profile


class RegistrationForm(forms.Form):
    university_id = forms.CharField(label="University ID", max_length=150)
    first_name = forms.CharField(label="First name", max_length=150)
    last_name = forms.CharField(label="Last name", max_length=150)
    email = forms.EmailField(required=True)
    age = forms.IntegerField(label="Age", min_value=1, max_value=120)
    home_address = forms.CharField(label="Home address", widget=forms.Textarea(attrs={"rows": 3}))
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    def clean_university_id(self):
        university_id = self.cleaned_data["university_id"].strip()
        if User.objects.filter(username=university_id).exists():
            raise forms.ValidationError("That University ID is already registered.")
        return university_id

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password1") != cleaned_data.get("password2"):
            self.add_error("password2", "Passwords do not match.")
        return cleaned_data

    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data["university_id"],
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password1"],
        )
        Profile.objects.create(
            user=user,
            age=self.cleaned_data["age"],
            home_address=self.cleaned_data["home_address"],
        )
        return user
