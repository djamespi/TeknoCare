from django.urls import path

from . import availability_views as views

app_name = "availability"
urlpatterns = [
    path("", views.slot_list, name="list"),
    path("new/", views.slot_edit, name="create"),
    path("<int:pk>/", views.slot_edit, name="edit"),
]
