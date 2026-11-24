from django import forms
from django.db.models import Q

from apps.appointments.models import Appointment
from apps.clinical.models import MedicalRecord
from .models import Medication, PrescriptionItem
from .services import ITEM_FIELDS


class MedicationForm(forms.ModelForm):
    class Meta:
        model = Medication
        fields = ("medication_code", "generic_name", "strength", "dosage_form", "is_active")


class PrescriptionItemForm(forms.ModelForm):
    expected_version = forms.CharField(widget=forms.HiddenInput, max_length=64)

    class Meta:
        model = PrescriptionItem
        fields = ("medication", *ITEM_FIELDS)
        widgets = {"instructions": forms.Textarea(attrs={"rows": 3})}
        help_texts = {"medication": "Choose the exact strength and dosage form from the catalog."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["medication"].queryset = Medication.objects.filter(is_active=True).order_by("generic_name", "medication_code")


class PrescriptionActionForm(forms.Form):
    expected_version = forms.CharField(widget=forms.HiddenInput, max_length=64)
    confirm = forms.BooleanField(label="I confirm this action")


class EncounterChoice(forms.ModelChoiceField):
    def label_from_instance(self, visit):
        return f"Encounter #{visit.pk} · {visit.chief_complaint or 'Draft intake'}"


class ReplacementForm(forms.Form):
    encounter = EncounterChoice(queryset=MedicalRecord.objects.none(), label="Draft encounter")

    def __init__(self, *args, patient_id, provider_id, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["encounter"].queryset = MedicalRecord.objects.filter(
            patient_id=patient_id, provider_id=provider_id, status=MedicalRecord.Status.DRAFT,
        ).filter(Q(appointment__isnull=True) | Q(appointment__status=Appointment.Status.CHECKED_IN)).order_by("-visited_at", "-pk")
