from django import forms

from apps.billing.forms import TermFilterForm


class DateRangeForm(forms.Form):
    from_date = forms.DateField(label="From date", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    through_date = forms.DateField(label="Through date", required=False, widget=forms.DateInput(attrs={"type": "date"}))

    def clean(self):
        values = super().clean()
        start, end = values.get("from_date"), values.get("through_date")
        if start and end and end < start:
            self.add_error("through_date", "Choose a date on or after From date.")
        return values


class AuditFilterForm(DateRangeForm):
    actor = forms.CharField(label="Actor university ID", max_length=20, required=False)
    action = forms.CharField(max_length=100, required=False)
    target_table = forms.CharField(max_length=50, required=False)
    target_id = forms.IntegerField(label="Target ID", min_value=-2147483648, max_value=2147483647, required=False)


class ReportFilterForm(DateRangeForm, TermFilterForm):
    field_order = ("from_date", "through_date", "term")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["term"].label = "Tuition term"
