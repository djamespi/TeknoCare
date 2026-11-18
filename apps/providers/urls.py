from django.urls import path

from . import views

app_name = "providers"
urlpatterns = [
    path("", views.provider_list, name="provider_list"),
    path("new/", views.provider_create, name="provider_create"),
    path("attach/", views.provider_attach, name="provider_attach"),
    path("<int:pk>/", views.provider_edit, name="provider_edit"),
]
