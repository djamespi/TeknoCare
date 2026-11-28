"""Portal actions for the profile feature."""
from apps.common.web import validated
from apps.profile.forms import ProfileForm
from apps.profile.models import Profile


def profile(actor, data):
    form = ProfileForm(data, instance=Profile.objects.filter(user=actor).first() or Profile(user=actor))
    validated(form)
    form.save()
