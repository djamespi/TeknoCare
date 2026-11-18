from django import forms

from .models import Department


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ("code", "name", "is_active")
        help_texts = {"code": "Use a supplied or clearly fictional code. A referenced code cannot be changed."}
