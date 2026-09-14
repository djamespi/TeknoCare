from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home:home")

    error = None
    if request.method == "POST":
        university_id = request.POST.get("university_id", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=university_id, password=password)
        if user is not None:
            login(request, user)
            return redirect("home:home")
        error = "Invalid username or password."

    return render(request, "login/login.html", {"error": error})
