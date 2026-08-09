from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.loyalty.models import LoyaltyAccount, LoyaltyTransaction

from .emails import send_order_confirmation_email
from .models import Order


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
    send_order_confirmation_email(order)
    return order
