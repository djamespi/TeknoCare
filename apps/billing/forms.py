from decimal import Decimal

from django import forms

from .models import AcademicTerm, StudentCharge


class AcademicTermForm(forms.ModelForm):
    class Meta:
        model = AcademicTerm
        fields = ("academic_year", "semester", "start_date", "end_date", "is_open_for_charges")
        widgets = {"start_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "end_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}
        help_texts = {"semester": "Use a supplied or fictional term label; no official university calendar is preloaded.",
            "is_open_for_charges": "Allow charge creation and simulated posting for this term."}


class TermFilterForm(forms.Form):
    term = forms.ModelChoiceField(required=False, queryset=AcademicTerm.objects.order_by("-start_date", "-pk"),
        empty_label="All terms")


class ChargeFilterForm(TermFilterForm):
    status = forms.ChoiceField(required=False, choices=[("", "All statuses"), *StudentCharge.Status.choices])


class ChargeCreateForm(forms.Form):
    request_code = forms.UUIDField(widget=forms.HiddenInput)
    term = forms.ModelChoiceField(queryset=AcademicTerm.objects.order_by("-start_date", "-pk"))
    description = forms.ChoiceField(choices=[
        ("Clinic service (prototype)", "Clinic service (prototype)"),
        ("Medication charge (prototype)", "Medication charge (prototype)"),
    ])
    amount = forms.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        term = self.fields["term"]
        # Accept a closed term ID so the service can match an already completed request.
        open_terms = forms.ModelChoiceField(queryset=term.queryset.filter(is_open_for_charges=True))
        term.widget.choices = open_terms.choices


class SimulatedPostingForm(forms.Form):
    confirm = forms.BooleanField(label="Confirm simulated tuition acknowledgment")


class VoidChargeForm(forms.Form):
    expected_status = forms.ChoiceField(widget=forms.HiddenInput, choices=[
        (StudentCharge.Status.PENDING, "Pending"), (StudentCharge.Status.POSTED, "Posted"),
    ])
    reason = forms.CharField(label="Administrative reason", max_length=500, widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Use a brief administrative explanation. Keep clinical notes in the encounter.")
    confirm = forms.BooleanField(label="Confirm void")

    def __init__(self, *args, posted=False, **kwargs):
        super().__init__(*args, **kwargs)
        if posted:
            self.fields["confirm"].label = "Confirm simulated tuition reversal"
