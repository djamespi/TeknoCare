from django.contrib import admin

from .models import User


@admin.register(User)
class ClinicUserAdmin(admin.ModelAdmin):
    list_display = ("school_id", "fname", "lname", "user_type", "account_status")
    search_fields = ("school_id", "fname", "lname", "email")
    list_filter = ("user_type", "account_status")
    fields = ("school_id", "fname", "lname", "email", "user_type", "account_status", "created_at")
    readonly_fields = fields
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
