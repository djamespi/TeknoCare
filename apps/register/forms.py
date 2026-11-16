from django import forms
from django.db import transaction

from apps.patients.models import Affiliation, EmergencyContact, Patient
from .models import User


class RegistrationForm(forms.Form):
    university_id = forms.CharField(label="University ID", max_length=20)
    first_name = forms.CharField(label="First name", max_length=50)
    last_name = forms.CharField(label="Last name", max_length=50)
    email = forms.EmailField(required=True, max_length=100)
    emergency_contact_name = forms.CharField(label="Emergency contact name", max_length=150)
    emergency_contact_relationship = forms.CharField(label="Relationship", max_length=50)
    emergency_contact = forms.CharField(label="Emergency contact phone", max_length=30)
    medical_history_summary = forms.CharField(
        label="Medical history summary",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    def clean_university_id(self):
        university_id = self.cleaned_data["university_id"].strip()
        if User.objects.filter(school_id=university_id).exists():
            raise forms.ValidationError("That University ID is already registered.")
        return university_id

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password1") != cleaned_data.get("password2"):
            self.add_error("password2", "Passwords do not match.")
        return cleaned_data

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("That email is already registered.")
        return email

    @transaction.atomic
    def save(self):
        user = User.objects.create_user(
            school_id=self.cleaned_data["university_id"],
            fname=self.cleaned_data["first_name"],
            lname=self.cleaned_data["last_name"],
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password1"],
            user_type=User.UserType.PATIENT,
            account_status=User.AccountStatus.ACTIVE,
        )
        patient = Patient.objects.create(
            patient=user,
            affiliation=Affiliation.STUDENT,
            medical_history_summary=self.cleaned_data["medical_history_summary"],
        )
        EmergencyContact.objects.create(patient=patient,
            full_name=self.cleaned_data["emergency_contact_name"],
            relationship=self.cleaned_data["emergency_contact_relationship"],
            phone_number=self.cleaned_data["emergency_contact"], is_primary=True)
        return user
