from django.urls import path

from .views import join_demo


app_name = "joins"
urlpatterns = [path("", join_demo, name="demo")]
