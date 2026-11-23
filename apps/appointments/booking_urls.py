from django.urls import path

from . import booking_views as views

app_name = "booking"
urlpatterns = [
    path("", views.appointment_list, name="list"),
    path("available/", views.slot_browse, name="browse"),
    path("available/<int:slot_id>/", views.slot_book, name="book"),
    path("<int:appointment_id>/", views.appointment_detail, name="detail"),
    path("<int:appointment_id>/cancel/", views.appointment_cancel, name="cancel"),
    path("<int:appointment_id>/reschedule/", views.slot_browse, name="reschedule"),
    path("<int:appointment_id>/reschedule/<int:slot_id>/", views.slot_book, name="confirm_reschedule"),
]
