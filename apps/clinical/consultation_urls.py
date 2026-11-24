from django.urls import path

from . import consultation_views as views
from . import referral_views

app_name = "consultation"
urlpatterns = [
    path("", views.worklist, name="list"),
    path("encounters/<int:pk>/", views.workspace, name="workspace"),
    path("encounters/<int:record_id>/referrals/", referral_views.referral_list, name="referrals"),
    path("encounters/<int:record_id>/referrals/new/", referral_views.referral_create, name="referral_create"),
    path("encounters/<int:record_id>/referrals/<int:pk>/follow-up/", referral_views.referral_follow_up, name="referral_follow_up"),
    path("diagnoses/", views.diagnosis_list, name="diagnosis_list"),
    path("diagnoses/new/", views.diagnosis_create, name="diagnosis_create"),
]
