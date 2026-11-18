from django import forms

from .models import AcademicTerm


class AcademicTermForm(forms.ModelForm):
    class Meta:
        model = AcademicTerm
        fields = ("academic_year", "semester", "start_date", "end_date", "is_open_for_charges")
        widgets = {"start_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "end_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}
        help_texts = {"semester": "Use a supplied or fictional term label; no official university calendar is preloaded.",
            "is_open_for_charges": "Allows later charge creation/posting only. This does not collect payments or connect to university finance."}
