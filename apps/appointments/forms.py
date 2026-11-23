from django import forms
from django.db.models import Q

from apps.providers.eligibility import eligible_providers
from apps.providers.models import Provider

from .models import ClinicRoom, Slot


class ClinicRoomForm(forms.ModelForm):
    class Meta:
        model = ClinicRoom
        fields = ("campus", "building", "room_number", "is_active")
        help_texts = {"is_active": "Deactivation is blocked while unresolved bookings exist. Unbooked future availability is disabled, not deleted."}


class ProviderChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, provider):
        return f"{provider.provider.get_full_name()} ({provider.provider.school_id})"


class AvailabilityFilterForm(forms.Form):
    from_date = forms.DateField(label="From date", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    through_date = forms.DateField(label="Through date", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    provider = ProviderChoiceField(queryset=Provider.objects.none(), required=False, empty_label="All providers")

    def __init__(self, *args, admin=False, **kwargs):
        super().__init__(*args, **kwargs)
        if admin:
            self.fields["provider"].queryset = Provider.objects.select_related("provider").order_by("provider__school_id")
        else:
            self.fields.pop("provider")

    def clean(self):
        values = super().clean()
        start, end = values.get("from_date"), values.get("through_date")
        if start and end and end < start:
            self.add_error("through_date", "Choose a date on or after From date.")
        return values


class SlotForm(forms.Form):
    provider = ProviderChoiceField(queryset=Provider.objects.none())
    room = forms.ModelChoiceField(queryset=ClinicRoom.objects.none())
    start_time = forms.DateTimeField(
        label="Start time", widget=forms.DateTimeInput(format="%Y-%m-%dT%H:%M:%S", attrs={"type": "datetime-local", "step": "1"}),
    )
    end_time = forms.DateTimeField(
        label="End time", widget=forms.DateTimeInput(format="%Y-%m-%dT%H:%M:%S", attrs={"type": "datetime-local", "step": "1"}),
    )
    is_active = forms.BooleanField(label="Open for booking", required=False, initial=True)
    expected_version = forms.CharField(max_length=40, widget=forms.HiddenInput)

    def __init__(self, *args, admin=False, slot: Slot | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.slot = slot
        if admin:
            providers = eligible_providers()
            if slot:
                providers = providers | Provider.objects.filter(pk=slot.provider_id)
            self.fields["provider"].queryset = providers.select_related("provider").order_by("provider__school_id")
        else:
            self.fields.pop("provider")

        rooms = Q(is_active=True)
        if slot:
            rooms |= Q(pk=slot.room_id)
            self.initial.update(
                provider=slot.provider_id, room=slot.room_id, start_time=slot.start_time,
                end_time=slot.end_time, is_active=slot.is_active, expected_version=slot.version,
            )
            self.fields["room"].required = slot.room_id is not None
            if slot.has_appointment:
                for name in ("provider", "room", "start_time", "end_time"):
                    if name in self.fields:
                        self.fields[name].disabled = True
        else:
            self.fields.pop("expected_version")
        self.fields["room"].queryset = ClinicRoom.objects.filter(rooms).order_by("campus", "building", "room_number", "pk")

    def clean(self):
        values = super().clean()
        if self.slot:
            for name in ("start_time", "end_time"):
                previous = getattr(self.slot, name)
                if values.get(name) == previous.replace(microsecond=0):
                    values[name] = previous
        start, end = values.get("start_time"), values.get("end_time")
        if start and end and end <= start:
            self.add_error("end_time", "Slot must end after it starts.")
        return values
