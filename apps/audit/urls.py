from django.urls import path

from . import views

app_name = "audit"
urlpatterns = [
    path("audit/", views.audit_list, name="history"),
    path("reports/", views.reports, name="reports"),
]
