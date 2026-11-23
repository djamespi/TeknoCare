from django import forms

from apps.appointments.forms import ProviderChoiceField
from apps.providers.eligibility import eligible_providers
from apps.providers.models import Provider


class AttendingProviderForm(forms.Form):
    provider = ProviderChoiceField(label="Attending provider", queryset=Provider.objects.none())

    def __init__(self, *args, patient_id, fixed=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["provider"].queryset = eligible_providers().exclude(pk=patient_id).select_related(
            "provider"
        ).order_by("provider__school_id")
        self.fields["provider"].disabled = fixed


class AssignmentForm(AttendingProviderForm):
    expected_provider_id = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
