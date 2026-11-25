from django.urls import path

from . import views

app_name = "portal"
urlpatterns = [
    path("", views.index, name="index"),
    path("session/", views.snapshot, name="snapshot"),
    path("actions/<slug:name>/", views.action, name="action"),
]
