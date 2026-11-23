from django.urls import path

from . import reception_views as views

app_name = "reception"
urlpatterns = [
    path("", views.queue, name="queue"),
    path("appointments/<int:pk>/", views.appointment, name="appointment"),
    path("walk-in/", views.walkin_lookup, name="walkin_lookup"),
    path("walk-in/<int:pk>/", views.walkin_create, name="walkin_create"),
    path("encounters/<int:pk>/", views.encounter, name="encounter"),
]
