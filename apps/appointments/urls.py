from django.urls import path

from . import views

app_name = "appointments"
urlpatterns = [
    path("", views.room_list, name="room_list"),
    path("new/", views.room_edit, name="room_create"),
    path("<int:pk>/", views.room_edit, name="room_edit"),
]
