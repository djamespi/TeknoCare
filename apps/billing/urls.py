from django.urls import path

from . import charge_views, views

app_name = "billing"
urlpatterns = [
    path("clinic/terms/", views.term_list, name="term_list"),
    path("clinic/terms/new/", views.term_edit, name="term_create"),
    path("clinic/terms/<int:pk>/", views.term_edit, name="term_edit"),
    path("clinic/charges/", charge_views.charge_list, name="charges"),
    path("clinic/charges/find/", charge_views.charge_lookup, name="charge_lookup"),
    path("clinic/charges/encounters/<int:record_id>/", charge_views.charge_create, name="charge_create"),
    path("clinic/charges/<int:pk>/", charge_views.charge_detail, name="charge_detail"),
    path("clinic/charges/export/", charge_views.charge_export, name="charge_export"),
    path("charges/", charge_views.patient_charge_list, name="patient_charges"),
    path("charges/<int:pk>/", charge_views.patient_charge_detail, name="patient_charge_detail"),
]
