from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.accounts.models import Address
from apps.cart import services as cart_services
from apps.coupons.models import Coupon
from apps.loyalty.models import LoyaltyAccount
from apps.shipping.models import ShippingMethod

from .forms import CheckoutForm, ReturnRequestForm
from .models import Order, OrderItem
from .payments import PaymentError, get_provider
from .services import fulfill_paid_order


def _compute_discount(coupon, subtotal):
    if not coupon or not coupon.is_valid():
        return 0
    if coupon.discount_type == Coupon.DiscountType.PERCENT:
        return (subtotal * coupon.value / 100).quantize(Decimal("0.01"))
    return min(coupon.value, subtotal)


def checkout(request):
    cart = cart_services.get_cart(request, create=False)
    items = list(cart.items.select_related("variant__product").all()) if cart else []
    if not items:
        messages.error(request, _("Your cart is empty."))
        return redirect("cart:cart_detail")

    for item in items:
        if item.quantity > item.variant.stock_quantity:
            messages.error(
                request,
                _("Only %(stock)s left of %(name)s - please update your cart.")
                % {"stock": item.variant.stock_quantity, "name": item.variant.product.name},
            )
            return redirect("cart:cart_detail")

    subtotal = cart_services.cart_subtotal(cart)
    default_address = None
    if request.user.is_authenticated:
        default_address = Address.objects.filter(user=request.user, is_default=True).first()

    initial = {}
    if default_address:
        initial = {
            "shipping_full_name": default_address.full_name,
            "shipping_street": default_address.street,
            "shipping_city": default_address.city,
            "shipping_postal_code": default_address.postal_code,
            "shipping_country": default_address.country,
            "shipping_phone": default_address.phone,
        }

    available_points = 0
    if request.user.is_authenticated:
        loyalty_account = LoyaltyAccount.objects.filter(user=request.user).first()
        available_points = loyalty_account.points_balance if loyalty_account else 0

    coupon = None

    if request.method == "POST":
        form = CheckoutForm(
            request.POST, user_authenticated=request.user.is_authenticated, available_points=available_points
        )
        if form.is_valid():
            coupon_code = form.cleaned_data.get("coupon_code", "").strip()
            if coupon_code:
                coupon = Coupon.objects.filter(code__iexact=coupon_code).first()
                if not coupon or not coupon.is_valid():
                    form.add_error("coupon_code", _("This coupon code is invalid or has expired."))
                    coupon = None

        if form.is_valid():
            shipping_method = form.cleaned_data["shipping_method"]
            coupon_discount = _compute_discount(coupon, subtotal)

            remaining = max(subtotal - coupon_discount, 0)
            point_value = Decimal(str(settings.LOYALTY_POINT_VALUE_PLN))
            max_useful_points = int(remaining / point_value) if point_value else 0
            redeem_points = min(form.cleaned_data.get("redeem_points") or 0, max_useful_points, available_points)
            loyalty_discount = (Decimal(redeem_points) * point_value).quantize(Decimal("0.01"))

            discount = coupon_discount + loyalty_discount
            shipping_cost = shipping_method.cost_for(subtotal)
            total = max(0, subtotal - discount + shipping_cost)

            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                guest_email=form.cleaned_data.get("guest_email", ""),
                currency="PLN",
                subtotal=subtotal,
                discount_amount=discount,
                loyalty_points_redeemed=redeem_points,
                shipping_cost=shipping_cost,
                total=total,
                coupon=coupon,
                shipping_method=shipping_method,
                carrier=shipping_method.carrier,
                inpost_locker_point_id=form.cleaned_data.get("inpost_locker_point_id", ""),
                shipping_full_name=form.cleaned_data["shipping_full_name"],
                shipping_street=form.cleaned_data["shipping_street"],
                shipping_city=form.cleaned_data["shipping_city"],
                shipping_postal_code=form.cleaned_data["shipping_postal_code"],
                shipping_country=form.cleaned_data["shipping_country"],
                shipping_phone=form.cleaned_data.get("shipping_phone", ""),
            )
            for item in items:
                OrderItem.objects.create(
                    order=order,
                    variant=item.variant,
                    product_name=item.variant.product.name,
                    variant_attributes=item.variant.attributes,
                    unit_price=item.variant.current_price(),
                    quantity=item.quantity,
                    vat_rate=item.variant.product.vat_rate,
                )
            cart.items.all().delete()
            return redirect("orders:payment_select", order_number=order.order_number)
    else:
        form = CheckoutForm(
            initial=initial, user_authenticated=request.user.is_authenticated, available_points=available_points
        )

    inpost_method = ShippingMethod.objects.filter(requires_locker_selection=True).first()

    context = {
        "form": form,
        "items": items,
        "subtotal": subtotal,
        "inpost_method_id": inpost_method.id if inpost_method else "",
        "available_points": available_points,
        "point_value": settings.LOYALTY_POINT_VALUE_PLN,
    }
    return render(request, "orders/checkout.html", context)


def payment_select(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    return render(request, "orders/payment_select.html", {"order": order})


def payment_start(request, order_number, provider):
    order = get_object_or_404(Order, order_number=order_number)
    if order.payment_status == Order.PaymentStatus.PAID:
        return redirect("orders:payment_return", order_number=order.order_number)
    try:
        redirect_url = get_provider(provider).create_payment(order, request)
    except PaymentError as exc:
        messages.error(request, _("Could not start payment: %(error)s") % {"error": exc})
        return redirect("orders:payment_select", order_number=order.order_number)
    return redirect(redirect_url)


def payment_return(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    context = {
        "order": order,
        "status_eligible_for_return": [Order.Status.PAID, Order.Status.SHIPPED, Order.Status.DELIVERED],
    }
    return render(request, "orders/order_confirmation.html", context)


def mock_payment(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    return render(request, "orders/mock_payment.html", {"order": order})


@require_POST
def mock_confirm(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    fulfill_paid_order(order)
    return redirect("orders:payment_return", order_number=order.order_number)


@require_POST
def mock_cancel(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    order.status = Order.Status.CANCELLED
    order.cancelled_at = order.cancelled_at or timezone.now()
    order.save(update_fields=["status", "cancelled_at"])
    return redirect("orders:payment_return", order_number=order.order_number)


@csrf_exempt
@require_POST
def payu_webhook(request):
    from .payments import PayUProvider

    try:
        order = PayUProvider().confirm_from_webhook(request)
    except PaymentError:
        return HttpResponseBadRequest("invalid signature")
    if order:
        fulfill_paid_order(order)
    return HttpResponse(status=200)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    from .payments import StripeProvider

    try:
        order = StripeProvider().confirm_from_webhook(request)
    except PaymentError:
        return HttpResponseBadRequest("invalid signature")
    if order:
        fulfill_paid_order(order)
    return HttpResponse(status=200)


@login_required
def request_return(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    if order.status not in (Order.Status.PAID, Order.Status.SHIPPED, Order.Status.DELIVERED):
        messages.error(request, _("This order isn't eligible for a return yet."))
        return redirect("order_account:detail", order_number=order.order_number)

    if request.method == "POST":
        form = ReturnRequestForm(request.POST, order=order)
        if form.is_valid():
            return_request = form.save(commit=False)
            return_request.order = order
            return_request.user = request.user
            return_request.save()
            messages.success(request, _("Your return request has been submitted."))
            return redirect("order_account:detail", order_number=order.order_number)
    else:
        form = ReturnRequestForm(order=order)

    return render(request, "orders/request_return.html", {"form": form, "order": order})


def download_invoice(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    is_owner = request.user.is_authenticated and order.user_id == request.user.id
    if not (is_owner or request.user.is_staff):
        raise Http404
    if not hasattr(order, "invoice") or not order.invoice.pdf_file:
        raise Http404
    return redirect(order.invoice.pdf_file.url)


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "orders/order_history.html", {"orders": orders})


@login_required
def order_detail(request, order_number):
    order = get_object_or_404(
        Order.objects.prefetch_related("items", "return_requests"), order_number=order_number, user=request.user
    )
    context = {
        "order": order,
        "status_eligible_for_return": [Order.Status.PAID, Order.Status.SHIPPED, Order.Status.DELIVERED],
    }
    return render(request, "orders/order_detail.html", context)
