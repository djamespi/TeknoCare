from django.urls import path

from . import views

app_name = "prescriptions"
urlpatterns = [
    path("", views.patient_history, name="history"),
    path("<int:pk>/print/", views.print_detail, name="print"),
    path("catalog/", views.medication_list, name="catalog"),
    path("formulary/", views.formulary, name="formulary"),
    path("catalog/new/", views.medication_edit, name="medication_create"),
    path("catalog/<int:pk>/", views.medication_edit, name="medication_edit"),
    path("encounters/<int:record_id>/", views.encounter, name="encounter"),
    path("encounters/<int:record_id>/<int:pk>/", views.detail, name="detail"),
    path("encounters/<int:record_id>/<int:pk>/items/add/", views.item_edit, name="item_create"),
    path("encounters/<int:record_id>/<int:pk>/items/<int:item_id>/", views.item_edit, name="item_edit"),
    path("encounters/<int:record_id>/<int:pk>/items/<int:item_id>/remove/", views.item_remove, name="item_remove"),
]
