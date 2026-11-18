from django.urls import path

from .views import admin_password_reset_view, login_view, password_change_view

app_name = "login"
urlpatterns = [
    path("", login_view, name="login"),
    path("password/", password_change_view, name="password_change"),
    path("reset-password/", admin_password_reset_view, name="admin_password_reset"),
]
