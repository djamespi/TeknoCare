from django.urls import path

from . import consultation_views as views

app_name = "consultation"
urlpatterns = [
    path("", views.worklist, name="list"),
    path("encounters/<int:pk>/", views.workspace, name="workspace"),
    path("diagnoses/", views.diagnosis_list, name="diagnosis_list"),
    path("diagnoses/new/", views.diagnosis_create, name="diagnosis_create"),
]
