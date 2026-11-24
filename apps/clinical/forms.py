from django import forms

from apps.appointments.forms import ProviderChoiceField
from apps.providers.eligibility import eligible_providers
from apps.providers.models import Provider
from .models import Diagnosis, Referral, VitalSign


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


class VitalSignForm(forms.ModelForm):
    expected_version = forms.CharField(widget=forms.HiddenInput, max_length=64)

    class Meta:
        model = VitalSign
        fields = ("temperature_c", "systolic_mmhg", "diastolic_mmhg", "pulse_bpm",
            "respiratory_rate", "oxygen_saturation_pct", "height_cm", "weight_kg")
        labels = {
            "temperature_c": "Temperature (°C)", "systolic_mmhg": "Systolic (mmHg)",
            "diastolic_mmhg": "Diastolic (mmHg)", "pulse_bpm": "Pulse (bpm)",
            "respiratory_rate": "Respiratory rate (breaths/min)", "oxygen_saturation_pct": "Oxygen saturation (%)",
            "height_cm": "Height (cm)", "weight_kg": "Weight (kg)",
        }

    def clean(self):
        values = super().clean()
        if not self.errors and all(values.get(field) is None for field in self.Meta.fields):
            raise forms.ValidationError("Enter at least one recorded measurement.")
        if (values.get("systolic_mmhg") is None) != (values.get("diastolic_mmhg") is None):
            raise forms.ValidationError("Enter both blood pressure readings together.")
        return values


class ConsultationForm(forms.Form):
    expected_version = forms.CharField(widget=forms.HiddenInput, max_length=64)
    chief_complaint = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
    symptoms = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    examination_notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    treatment_plan = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    diagnoses = forms.ModelMultipleChoiceField(
        queryset=Diagnosis.objects.order_by("coding_system", "code"), required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    primary_diagnosis = forms.ModelChoiceField(
        queryset=Diagnosis.objects.order_by("coding_system", "code"), required=False,
        help_text="If selected, the primary diagnosis must also be checked above.",
    )

    def clean(self):
        values = super().clean()
        primary = values.get("primary_diagnosis")
        diagnoses = values.get("diagnoses")
        widget = self.fields["diagnoses"].widget
        submitted = widget.value_from_datadict(self.data, self.files, self.add_prefix("diagnoses")) or ()
        if diagnoses is not None and len(submitted) != len(diagnoses):
            self.add_error("diagnoses", "Choose each diagnosis only once.")
        if primary and primary not in values.get("diagnoses", ()):
            self.add_error("primary_diagnosis", "Select the primary diagnosis in the diagnoses list too.")
        return values


class FinalizeConsultationForm(forms.Form):
    expected_version = forms.CharField(widget=forms.HiddenInput, max_length=64)
    confirm = forms.BooleanField(label="I reviewed the saved consultation and confirm finalization")


class DiagnosisForm(forms.ModelForm):
    class Meta:
        model = Diagnosis
        fields = ("coding_system", "code", "description")
        help_texts = {"coding_system": "Use supplied catalog entries or a clearly fictional coding system for the demonstration."}


class ReferralForm(forms.ModelForm):
    class Meta:
        model = Referral
        fields = ("destination", "reason")
        labels = {"reason": "Patient-facing reason and instructions"}
        widgets = {"reason": forms.Textarea(attrs={"rows": 4})}
        help_texts = {"reason": "Write what the patient should see on their finalized visit summary. Keep private clinical notes in the consultation."}


class ReferralFollowUpForm(forms.Form):
    status = forms.ChoiceField(label="Follow-up status", choices=[
        (Referral.Status.COMPLETED, "Completed"), (Referral.Status.CANCELED, "Canceled"),
    ])
    confirm = forms.BooleanField(label="I confirm this follow-up status")
