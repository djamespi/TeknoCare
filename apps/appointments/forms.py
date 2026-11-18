from django import forms

from .models import ClinicRoom


class ClinicRoomForm(forms.ModelForm):
    class Meta:
        model = ClinicRoom
        fields = ("campus", "building", "room_number", "is_active")
        help_texts = {"is_active": "Deactivation is blocked while unresolved bookings exist. Unbooked future availability is disabled, not deleted."}
