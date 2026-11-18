from django import forms

from apps.register.forms import AccountProvisionForm
from apps.register.models import User
from .models import Provider


class ProviderAccountForm(AccountProvisionForm):
    provider_type = forms.ChoiceField(choices=Provider.Type.choices, initial=Provider.Type.UNVERIFIED)
    license_number = forms.CharField(max_length=50, required=False, help_text="Optional: leave blank unless supplied and reviewed. Do not invent a license number.")
    specialization = forms.CharField(max_length=100, required=False)


class AccountChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, user):
        return f"{user.school_id} — {user.get_full_name()}"


class ProviderAttachForm(forms.Form):
    user = AccountChoiceField(queryset=User.objects.none(), label="Existing Admin/Provider account",
        help_text="Only accounts without a Provider profile appear. This does not change account role or password.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = User.objects.filter(user_type__in=["Admin", "Provider"], provider_profile__isnull=True).order_by("school_id")


class ProviderForm(forms.ModelForm):
    verification_confirmed = forms.BooleanField(required=False, label="I reviewed the provider designation and supplied credentials",
        help_text="Required for activation or a designation change. Prototype manual review only, not professional-license verification or evidence storage.")

    class Meta:
        model = Provider
        fields = ("provider_type", "license_number", "specialization", "is_active")
        labels = {"is_active": "Clinically active"}
        help_texts = {"license_number": "Optional: blank is stored as NULL. Never fabricate a credential.",
            "is_active": "Needs an Active Admin/Provider account and known designation. Account suspension is managed separately."}
