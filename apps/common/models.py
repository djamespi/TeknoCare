"""Small persistence primitives; feature rules stay in their owning app."""
from django.db import models, router, transaction


class ValidatedModel(models.Model):
    """Validate normal saves; SQL/bulk writes still require DB constraints.

    Serialize updates to the same row so model transition checks see committed
    state. Bulk updates deliberately bypass this API and must not implement
    clinical or billing transitions.
    """

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        alias = kwargs.get("using") or router.db_for_write(type(self), instance=self)
        with transaction.atomic(using=alias):
            if self.pk and not self._state.adding:
                type(self).objects.using(alias).select_for_update().filter(pk=self.pk).exists()
            self.full_clean()
            return super().save(*args, **kwargs)
