from django import forms
from django.db.models import Q
from django.utils import timezone

from apps.register.forms import AccountProvisionForm
from apps.university.models import Department

from .models import Affiliation, PatientAllergy


class BirthDateForm(forms.Form):
    date_of_birth = forms.DateField(
        label="Date of birth",
        required=False,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date", "autocomplete": "bday"}),
    )

    def clean_date_of_birth(self):
        value = self.cleaned_data["date_of_birth"]
        if value and value > timezone.localdate():
            raise forms.ValidationError("Birth date cannot be in the future.")
        return value


class EmergencyContactForm(forms.Form):
    full_name = forms.CharField(max_length=150)
    relationship = forms.CharField(max_length=50)
    phone_number = forms.CharField(max_length=30, widget=forms.TextInput(attrs={"type": "tel"}))
    is_primary = forms.BooleanField(
        label="Primary contact", required=False, help_text="Selecting this replaces any current primary contact."
    )


class AllergyForm(forms.Form):
    allergen = forms.CharField(max_length=150)
    reaction = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    severity = forms.ChoiceField(choices=PatientAllergy.Severity.choices, initial=PatientAllergy.Severity.UNKNOWN)


class UniversityIDForm(forms.Form):
    school_id = forms.CharField(label="Exact University ID", max_length=20)


class PatientFilterForm(forms.Form):
    q = forms.CharField(label="University ID or name", max_length=100, required=False)
    affiliation = forms.ChoiceField(
        required=False, choices=[("", "All affiliations"), ("unknown", "Awaiting review"), *Affiliation.choices]
    )


class AffiliationForm(forms.Form):
    affiliation = forms.ChoiceField(choices=[("", "Select affiliation"), *Affiliation.choices])
    department = forms.ModelChoiceField(queryset=Department.objects.none(), required=False)
    confirm = forms.BooleanField(label="I confirm these university affiliation details for this prototype")

    def __init__(self, *args, patient=None, **kwargs):
        super().__init__(*args, **kwargs)
        departments = Q(is_active=True)
        if patient and patient.department_id:
            departments |= Q(pk=patient.department_id)
        self.fields["department"].queryset = Department.objects.filter(departments)
        if patient and patient.affiliation is None:
            self.fields["affiliation"].required = False
            self.fields["affiliation"].choices = [("", "Awaiting review"), *Affiliation.choices]

    def affiliation_values(self):
        return {
            "affiliation": self.cleaned_data["affiliation"] or None,
            "department": self.cleaned_data["department"],
        }


class AttachPatientForm(BirthDateForm, AffiliationForm):
    field_order = ("affiliation", "department", "date_of_birth", "confirm")


class NewPatientAccountForm(AccountProvisionForm, AttachPatientForm):
    field_order = (*AccountProvisionForm.base_fields, *AttachPatientForm.field_order)


class PatientIdentityForm(forms.Form):
    school_id = forms.CharField(label="University ID", max_length=20)
    first_name = forms.CharField(max_length=50)
    last_name = forms.CharField(max_length=50)
    email = forms.EmailField(max_length=100)
    confirm = forms.BooleanField(label="I confirm the corrected account identity")
