from django.urls import path

from . import views

app_name = "university"
urlpatterns = [
    path("", views.management_home, name="management"),
    path("departments/", views.department_list, name="department_list"),
    path("departments/new/", views.department_edit, name="department_create"),
    path("departments/<int:pk>/", views.department_edit, name="department_edit"),
]
