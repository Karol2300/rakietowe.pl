from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import ProductVariant
from apps.coupons.models import Coupon
from apps.shipping.models import Carrier, ShippingMethod


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        PAID = "paid", _("Paid")
        SHIPPED = "shipped", _("Shipped")
        DELIVERED = "delivered", _("Delivered")
        CANCELLED = "cancelled", _("Cancelled")
        RETURNED = "returned", _("Returned")

    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", _("Unpaid")
        PAID = "paid", _("Paid")
        REFUNDED = "refunded", _("Refunded")

    class PaymentProvider(models.TextChoices):
        PAYU = "payu", _("PayU")
        STRIPE = "stripe", _("Stripe")

    order_number = models.CharField(max_length=32, unique=True, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )
    guest_email = models.EmailField(blank=True)

    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    payment_status = models.CharField(
        max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID
    )
    payment_provider = models.CharField(max_length=10, choices=PaymentProvider.choices, blank=True)
    payment_reference = models.CharField(max_length=255, blank=True)

    currency = models.CharField(max_length=3, default="PLN")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    loyalty_points_redeemed = models.PositiveIntegerField(default=0)
    shipping_cost = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    coupon = models.ForeignKey(
        Coupon, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )

    shipping_method = models.ForeignKey(
        ShippingMethod, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )
    carrier = models.CharField(max_length=10, choices=Carrier.choices, blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)
    inpost_locker_point_id = models.CharField(max_length=50, blank=True)

    shipping_full_name = models.CharField(max_length=255)
    shipping_street = models.CharField(max_length=255)
    shipping_city = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=20)
    shipping_country = models.CharField(max_length=2, default="PL")
    shipping_phone = models.CharField(max_length=30, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.order_number or f"Order #{self.pk}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            import uuid

            self.order_number = f"RS-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.PROTECT, related_name="order_items"
    )
    product_name = models.CharField(max_length=255)
    variant_attributes = models.JSONField(default=dict, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def line_total(self):
        return self.unit_price * self.quantity


class Invoice(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="invoice")
    invoice_number = models.CharField(max_length=32, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to="invoices/", blank=True)

    def __str__(self):
        return self.invoice_number


class ReturnRequest(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", _("Requested")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")
        REFUNDED = "refunded", _("Refunded")

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="return_requests")
    item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name="return_requests")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="return_requests")
    quantity = models.PositiveIntegerField(default=1)
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.REQUESTED)
    staff_notes = models.TextField(blank=True)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
