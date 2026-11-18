"""Custom-user authentication with active-account and required-profile checks."""
from asgiref.sync import sync_to_async
from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import MultipleObjectsReturned

from apps.common.permissions import required_profile_exists


class ClinicBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            return super().authenticate(request, username=username, password=password, **kwargs)
        except MultipleObjectsReturned:
            return None

    def user_can_authenticate(self, user):
        return super().user_can_authenticate(user) and required_profile_exists(user)

    async def aauthenticate(self, request, username=None, password=None, **kwargs):
        return await sync_to_async(self.authenticate)(request, username=username, password=password, **kwargs)

    async def aget_user(self, user_id):
        return await sync_to_async(self.get_user)(user_id)

    def get_user_permissions(self, user_obj, obj=None):
        if user_obj.is_active and user_obj.is_staff:
            return set(user_obj.ADMIN_VIEW_PERMISSIONS)
        return set()

    def get_group_permissions(self, user_obj, obj=None):
        return set()

    def get_all_permissions(self, user_obj, obj=None):
        return self.get_user_permissions(user_obj, obj)

    async def aget_user_permissions(self, user_obj, obj=None):
        return self.get_user_permissions(user_obj, obj)

    async def aget_group_permissions(self, user_obj, obj=None):
        return set()

    async def aget_all_permissions(self, user_obj, obj=None):
        return self.get_all_permissions(user_obj, obj)
