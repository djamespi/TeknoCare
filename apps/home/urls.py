from django.urls import path

from .views import home_view

app_name = "home"
urlpatterns = [
    path("", home_view, name="home"),
    path("dashboard/", home_view, name="dashboard"),
]
