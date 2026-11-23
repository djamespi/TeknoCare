from django import forms
from django.contrib.auth.password_validation import password_validators_help_text_html, validate_password

from .identity import identity_matches, normalize_email, normalize_school_id
from .models import User
from .services import register_student
from apps.patients.models import Affiliation
from apps.university.models import Department


class RegistrationForm(forms.Form):
    university_id = forms.CharField(label="University ID", max_length=20)
    first_name = forms.CharField(label="First name", max_length=50)
    last_name = forms.CharField(label="Last name", max_length=50)
    email = forms.EmailField(required=True, max_length=100)
    emergency_contact_name = forms.CharField(label="Emergency contact name", max_length=150)
    emergency_contact_relationship = forms.CharField(label="Relationship", max_length=50)
    emergency_contact = forms.CharField(label="Emergency contact phone", max_length=30)
    medical_history_summary = forms.CharField(
        label="Medical history summary (optional)",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    password1 = forms.CharField(label="Password", strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    password2 = forms.CharField(label="Confirm password", strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].help_text = password_validators_help_text_html()

    def clean_university_id(self):
        university_id = normalize_school_id(self.cleaned_data["university_id"])
        if identity_matches(User.objects.all(), school_id=university_id).exists():
            raise forms.ValidationError("That University ID is already registered.")
        return university_id

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password1") != cleaned_data.get("password2"):
            self.add_error("password2", "Passwords do not match.")
        if cleaned_data.get("password1"):
            candidate = User(school_id=cleaned_data.get("university_id", ""), email=cleaned_data.get("email", ""),
                fname=cleaned_data.get("first_name", ""), lname=cleaned_data.get("last_name", ""))
            try:
                validate_password(cleaned_data["password1"], candidate)
            except forms.ValidationError as error:
                self.add_error("password1", error)
        return cleaned_data

    def clean_email(self):
        email = normalize_email(self.cleaned_data["email"])
        if identity_matches(User.objects.all(), email=email).exists():
            raise forms.ValidationError("That email is already registered.")
        return email

    def save(self):
        return register_student(
            school_id=self.cleaned_data["university_id"],
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password1"],
            contact_name=self.cleaned_data["emergency_contact_name"],
            contact_relationship=self.cleaned_data["emergency_contact_relationship"],
            contact_phone=self.cleaned_data["emergency_contact"],
            medical_history_summary=self.cleaned_data["medical_history_summary"],
        )


class AccountProvisionForm(forms.Form):
    school_id = forms.CharField(label="University/personnel ID", max_length=20,
        help_text="Use a supplied or fictional ID. Case and leading zeros are preserved; no official personnel/provider ID format is assumed.")
    first_name = forms.CharField(max_length=50)
    last_name = forms.CharField(max_length=50)
    email = forms.EmailField(max_length=100)
    password1 = forms.CharField(label="Initial password", strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    password2 = forms.CharField(label="Confirm initial password", strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].help_text = password_validators_help_text_html()

    def clean_school_id(self):
        value = normalize_school_id(self.cleaned_data["school_id"])
        if identity_matches(User.objects.all(), school_id=value).exists():
            raise forms.ValidationError("That ID is already registered. Do not create a duplicate account.")
        return value

    def clean_email(self):
        value = normalize_email(self.cleaned_data["email"])
        if identity_matches(User.objects.all(), email=value).exists():
            raise forms.ValidationError("That email is already registered.")
        return value

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            self.add_error("password2", "Passwords do not match.")
        if cleaned.get("password1"):
            candidate = User(school_id=cleaned.get("school_id", ""), email=cleaned.get("email", ""),
                fname=cleaned.get("first_name", ""), lname=cleaned.get("last_name", ""))
            try:
                validate_password(cleaned["password1"], candidate)
            except forms.ValidationError as error:
                self.add_error("password1", error)
        return cleaned

    def account_values(self):
        return {"school_id": self.cleaned_data["school_id"], "email": self.cleaned_data["email"],
            "first_name": self.cleaned_data["first_name"], "last_name": self.cleaned_data["last_name"], "password": self.cleaned_data["password1"]}


class PersonnelAccountForm(AccountProvisionForm):
    affiliation = forms.ChoiceField(choices=[(Affiliation.FACULTY, "Faculty"), (Affiliation.STAFF, "Staff")])
    department = forms.ModelChoiceField(queryset=Department.objects.none(), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = Department.objects.filter(is_active=True)


class AccountStatusForm(forms.Form):
    account_status = forms.ChoiceField(choices=User.AccountStatus.choices)
    confirm = forms.BooleanField(label="I confirm this account access change", help_text="Suspension revokes sessions, not historical records. Existing bookings are preserved and may require clinic follow-up.")
