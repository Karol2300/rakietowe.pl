from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import RegistrationForm


def register(request):
    if request.user.is_authenticated:
        return redirect(reverse("core:home"))

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # triggers apps.cart.signals to merge the session cart
            next_url = request.POST.get("next") or reverse("core:home")
            return redirect(next_url)
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})
