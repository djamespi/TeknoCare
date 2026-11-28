"""Portal actions for the register feature."""
from apps.register.services import set_account_status


def account_status(actor, data):
    return set_account_status(actor=actor, user_id=data["id"], status=data["status"].title())
