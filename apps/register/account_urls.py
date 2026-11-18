from django.urls import path

from . import account_views

app_name = "accounts"
urlpatterns = [
    path("", account_views.personnel_list, name="personnel_list"),
    path("new/", account_views.personnel_create, name="personnel_create"),
    path("<int:pk>/status/", account_views.account_status, name="status"),
]
