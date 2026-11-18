from django.urls import path

from . import views

app_name = "billing"
urlpatterns = [
    path("", views.term_list, name="term_list"),
    path("new/", views.term_edit, name="term_create"),
    path("<int:pk>/", views.term_edit, name="term_edit"),
]
