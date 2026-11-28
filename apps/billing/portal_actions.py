"""Portal actions for the billing feature."""
from django.core.exceptions import ValidationError

from apps.billing.services import simulate_posting, simulate_void


def change_charge(actor, data):
    if data.get("confirm") is not True:
        raise ValidationError("Confirm this simulated change first.")
    if data["operation"] == "post":
        return simulate_posting(actor=actor, charge_id=data["id"], confirmed=True).pk
    if data["operation"] == "void":
        return simulate_void(actor=actor, charge_id=data["id"], reason=data["reason"],
                             expected_status=data["status"].title(), confirmed=True).pk
    raise ValidationError("Choose a valid charge action.")
