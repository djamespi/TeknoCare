from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .queries import get_join_results


@login_required
def join_demo(request):
    # GET executes SELECTs only. Sample creation is an explicit management command.
    return render(request, "joins/join_demo.html", get_join_results())
