from functools import wraps

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError

from .permissions import require_permission


def clinic_admin_required(view):
    @login_required
    @wraps(view)
    def authorized(request, *args, **kwargs):
        require_permission(request.user, "reference.manage")
        return view(request, *args, **kwargs)
    return authorized


def add_form_errors(form, error):
    if hasattr(error, "message_dict"):
        for field, errors in error.message_dict.items():
            form.add_error(field if field in form.fields else None, errors)
    else:
        form.add_error(None, error)


def validated(form):
    if not form.is_valid():
        raise ValidationError([error for errors in form.errors.values() for error in errors])
    return form.cleaned_data


class ReferenceFilterForm(forms.Form):
    q = forms.CharField(label="Search", required=False, max_length=100)
    state = forms.ChoiceField(label="Status", required=False,
        choices=[("", "All"), ("active", "Active"), ("inactive", "Inactive")])
