from django.urls import path

from . import intake_views as views

app_name = "patient_intake"
urlpatterns = [
    path("", views.patient_list, name="list"),
    path("new/", views.patient_create, name="create"),
    path("accounts/", views.account_lookup, name="account_lookup"),
    path("accounts/<int:pk>/", views.patient_attach, name="attach"),
    path("<int:pk>/affiliation/", views.affiliation_edit, name="affiliation"),
    path("<int:pk>/identity/", views.identity_edit, name="identity"),
]
