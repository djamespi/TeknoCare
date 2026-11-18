from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.common.web import ReferenceFilterForm, add_form_errors, clinic_admin_required
from .forms import ClinicRoomForm
from .models import ClinicRoom
from .services import save_room


@clinic_admin_required
@require_http_methods(["GET"])
def room_list(request):
    form = ReferenceFilterForm(request.GET)
    rooms = ClinicRoom.objects.order_by("campus", "building", "room_number", "pk")
    if form.is_valid():
        query = form.cleaned_data["q"]
        rooms = rooms.filter(Q(campus__icontains=query) | Q(building__icontains=query) | Q(room_number__icontains=query))
        if form.cleaned_data["state"]:
            rooms = rooms.filter(is_active=form.cleaned_data["state"] == "active")
    else:
        rooms = rooms.none()
    return render(request, "appointments/room_list.html", {"filter_form": form,
        "page_obj": Paginator(rooms, 10).get_page(request.GET.get("page"))})


@clinic_admin_required
@require_http_methods(["GET", "POST"])
def room_edit(request, pk=None):
    room = get_object_or_404(ClinicRoom, pk=pk) if pk else None
    form = ClinicRoomForm(request.POST if request.method == "POST" else None, instance=room)
    if request.method == "POST" and form.is_valid():
        try:
            save_room(actor=request.user, room_id=pk, **form.cleaned_data)
        except ValidationError as error:
            add_form_errors(form, error)
        except IntegrityError:
            form.add_error(None, "That room location was saved concurrently. Review its details and try again.")
        else:
            messages.success(request, "Clinic room saved. Existing bookings and visit history were preserved.")
            return redirect("appointments:room_list")
    return render(request, "includes/management_form.html", {"form": form, "title": "Edit clinic room" if pk else "Add clinic room",
        "description": "Use supplied or fictional locations. Referenced locations cannot be rewritten; deactivate or create another room.", "back_url": "appointments:room_list"})
