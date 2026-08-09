from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _

from apps.orders.models import Order

from .forms import AddressForm, ProfileForm, RegistrationForm
from .models import Address


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


@login_required
def dashboard(request):
    recent_orders = Order.objects.filter(user=request.user).order_by("-created_at")[:5]
    return render(request, "accounts/dashboard.html", {"recent_orders": recent_orders})


@login_required
def profile(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, _("Your profile has been updated."))
            return redirect("accounts:profile")
    else:
        form = ProfileForm(instance=request.user)
    return render(request, "accounts/profile.html", {"form": form})


@login_required
def address_list(request):
    addresses = Address.objects.filter(user=request.user)
    return render(request, "accounts/address_list.html", {"addresses": addresses})


@login_required
def address_form(request, address_id=None):
    address = get_object_or_404(Address, id=address_id, user=request.user) if address_id else None

    if request.method == "POST":
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            new_address = form.save(commit=False)
            new_address.user = request.user
            new_address.save()
            if new_address.is_default:
                Address.objects.filter(user=request.user).exclude(pk=new_address.pk).update(is_default=False)
            messages.success(request, _("Address saved."))
            return redirect("accounts:address_list")
    else:
        form = AddressForm(instance=address)

    return render(request, "accounts/address_form.html", {"form": form, "address": address})


@login_required
def address_delete(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    if request.method == "POST":
        address.delete()
        messages.success(request, _("Address removed."))
        return redirect("accounts:address_list")
    return render(request, "accounts/address_confirm_delete.html", {"address": address})


@login_required
def loyalty(request):
    from apps.loyalty.models import LoyaltyAccount

    account, _created = LoyaltyAccount.objects.get_or_create(user=request.user)
    transactions = account.transactions.order_by("-created_at")[:50]
    return render(request, "accounts/loyalty.html", {"account": account, "transactions": transactions})


@login_required
def payment_methods(request):
    used_providers = (
        Order.objects.filter(user=request.user, payment_status=Order.PaymentStatus.PAID)
        .exclude(payment_provider="")
        .values_list("payment_provider", flat=True)
        .distinct()
    )
    return render(request, "accounts/payment_methods.html", {"providers": set(used_providers)})
