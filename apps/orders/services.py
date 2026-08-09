from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.loyalty.models import LoyaltyAccount, LoyaltyTransaction

from .emails import (
    send_order_cancelled_email,
    send_order_confirmation_email,
    send_order_delivered_email,
    send_order_shipped_email,
    send_return_status_email,
)
from .invoicing import generate_invoice
from .models import Order
from .payments import get_provider


def award_loyalty_points(order):
    if not order.user:
        return
    account, _ = LoyaltyAccount.objects.get_or_create(user=order.user)
    points = int(order.total * Decimal(str(settings.LOYALTY_POINTS_PER_PLN)))
    if points <= 0:
        return
    account.points_balance += points
    account.save(update_fields=["points_balance"])
    LoyaltyTransaction.objects.create(
        account=account, order=order, kind=LoyaltyTransaction.Kind.EARNED, points=points
    )


@transaction.atomic
def fulfill_paid_order(order):
    """Called once a payment provider confirms payment. Idempotent: safe to
    call more than once (webhooks can retry/duplicate)."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.payment_status == Order.PaymentStatus.PAID:
        return order

    for item in order.items.select_related("variant"):
        variant = item.variant
        # Re-validate stock at payment confirmation time rather than at
        # checkout, so abandoned carts can't reserve inventory indefinitely.
        variant.stock_quantity = max(0, variant.stock_quantity - item.quantity)
        variant.save(update_fields=["stock_quantity"])

    order.payment_status = Order.PaymentStatus.PAID
    order.status = Order.Status.PAID
    order.paid_at = timezone.now()
    order.save(update_fields=["payment_status", "status", "paid_at"])

    if order.coupon:
        order.coupon.times_used += 1
        order.coupon.save(update_fields=["times_used"])

    award_loyalty_points(order)
    generate_invoice(order)
    send_order_confirmation_email(order)
    return order


def mark_shipped(order, tracking_number=""):
    if tracking_number:
        order.tracking_number = tracking_number
    order.status = Order.Status.SHIPPED
    order.shipped_at = order.shipped_at or timezone.now()
    order.save(update_fields=["tracking_number", "status", "shipped_at"])
    send_order_shipped_email(order)
    return order


def mark_delivered(order):
    order.status = Order.Status.DELIVERED
    order.delivered_at = order.delivered_at or timezone.now()
    order.save(update_fields=["status", "delivered_at"])
    send_order_delivered_email(order)
    return order


@transaction.atomic
def mark_cancelled(order):
    """Cancel an order, refunding the payment if it had already been paid."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    was_paid = order.payment_status == Order.PaymentStatus.PAID

    if was_paid and order.payment_provider:
        get_provider(order.payment_provider).refund(order, order.total)
        order.payment_status = Order.PaymentStatus.REFUNDED
        for item in order.items.select_related("variant"):
            item.variant.stock_quantity += item.quantity
            item.variant.save(update_fields=["stock_quantity"])

    order.status = Order.Status.CANCELLED
    order.cancelled_at = order.cancelled_at or timezone.now()
    order.save(update_fields=["status", "cancelled_at", "payment_status"])
    send_order_cancelled_email(order, refunded=was_paid)
    return order


@transaction.atomic
def process_return_refund(return_request):
    """Approve-and-refund a return request: refunds via the order's payment
    provider and restocks the returned quantity."""
    order = return_request.order
    amount = return_request.item.unit_price * return_request.quantity

    if order.payment_provider:
        get_provider(order.payment_provider).refund(order, amount)

    return_request.refund_amount = amount
    return_request.status = return_request.Status.REFUNDED
    return_request.save(update_fields=["refund_amount", "status", "updated_at"])

    variant = return_request.item.variant
    variant.stock_quantity += return_request.quantity
    variant.save(update_fields=["stock_quantity"])

    send_return_status_email(return_request)
    return return_request


def update_return_status(return_request, status):
    return_request.status = status
    return_request.save(update_fields=["status", "updated_at"])
    send_return_status_email(return_request)
    return return_request
