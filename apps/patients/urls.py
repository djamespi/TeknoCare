from django.urls import path

from . import views

app_name = "patients"
urlpatterns = [
    path("", views.patient_details, name="details"),
    path("birth-date/", views.birth_date, name="birth_date"),
    path("contacts/new/", views.contact_edit, name="contact_create"),
    path("contacts/<int:pk>/", views.contact_edit, name="contact_edit"),
    path("contacts/<int:pk>/remove/", views.contact_remove, name="contact_remove"),
    path("allergies/", views.allergy_lookup, name="allergy_lookup"),
    path("allergies/<int:patient_id>/", views.clinical_allergies, name="clinical_allergies"),
    path("allergies/<int:patient_id>/new/", views.allergy_edit, name="allergy_create"),
    path("allergies/<int:patient_id>/<int:pk>/", views.allergy_edit, name="allergy_edit"),
]
