import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.orders.models import Order

from .forms import AddressForm, ProfileForm, RegistrationForm
from .models import Address

logger = logging.getLogger(__name__)


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


@login_required
def privacy_data(request):
    return render(request, "accounts/privacy_data.html")


@login_required
def export_data(request):
    """GDPR Article 15/20: a self-service copy of the user's personal data
    in a portable format. Excludes internal-only fields (password hash,
    payment-provider customer refs) that aren't personal data the user
    needs a copy of."""
    user = request.user

    data = {
        "account": {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "date_joined": user.date_joined.isoformat(),
        },
        "addresses": [
            {
                "label": a.label,
                "full_name": a.full_name,
                "street": a.street,
                "city": a.city,
                "postal_code": a.postal_code,
                "country": a.country,
                "phone": a.phone,
                "is_default": a.is_default,
            }
            for a in user.addresses.all()
        ],
        "orders": [
            {
                "order_number": o.order_number,
                "status": o.status,
                "payment_status": o.payment_status,
                "total": str(o.total),
                "currency": o.currency,
                "shipping_full_name": o.shipping_full_name,
                "shipping_street": o.shipping_street,
                "shipping_city": o.shipping_city,
                "shipping_postal_code": o.shipping_postal_code,
                "shipping_country": o.shipping_country,
                "created_at": o.created_at.isoformat(),
                "items": [
                    {"product_name": i.product_name, "quantity": i.quantity, "unit_price": str(i.unit_price)}
                    for i in o.items.all()
                ],
            }
            for o in Order.objects.filter(user=user).prefetch_related("items")
        ],
        "reviews": [
            {
                "product": r.product.name,
                "rating": r.rating,
                "comment": r.comment,
                "created_at": r.created_at.isoformat(),
            }
            for r in user.reviews.select_related("product")
        ],
        "loyalty": _export_loyalty(user),
    }

    response = HttpResponse(json.dumps(data, indent=2, ensure_ascii=False), content_type="application/json")
    response["Content-Disposition"] = f'attachment; filename="my-data-{timezone.now().date()}.json"'
    return response


def _export_loyalty(user):
    from apps.loyalty.models import LoyaltyAccount

    account = LoyaltyAccount.objects.filter(user=user).first()
    if not account:
        return None
    return {
        "points_balance": account.points_balance,
        "transactions": [
            {"kind": t.kind, "points": t.points, "created_at": t.created_at.isoformat()}
            for t in account.transactions.all()
        ],
    }


@login_required
def delete_account(request):
    """GDPR Article 17 right to erasure. We anonymize rather than hard-delete:
    paid orders and their shipping/invoice snapshots must be kept for 5 years
    under Polish tax law (Ordynacja podatkowa), and Order.user is
    on_delete=SET_NULL so they survive independently of the account. Only
    account-identifying data and the reusable address book are removed."""
    if request.method == "POST":
        user = request.user
        original_email = user.email

        user.addresses.all().delete()

        user.email = f"deleted-user-{user.id}@deleted.racket-shop.example"
        user.username = f"deleted-user-{user.id}"
        user.first_name = ""
        user.last_name = ""
        user.stripe_customer_id = ""
        user.payu_customer_ref = ""
        user.is_active = False
        user.set_unusable_password()
        user.save()

        logout(request)

        try:
            message = render_to_string("accounts/email/account_deleted.txt", {"store_name": "Racket Sports Shop"})
            send_mail(
                "Your account has been deleted - Racket Sports Shop",
                message,
                settings.DEFAULT_FROM_EMAIL,
                [original_email],
            )
        except Exception:
            logger.exception("Failed to send account-deletion confirmation to %s", original_email)

        messages.success(request, _("Your account has been deleted."))
        return redirect("core:home")

    return render(request, "accounts/delete_account_confirm.html")
