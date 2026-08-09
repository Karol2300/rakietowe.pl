from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Coupon(models.Model):
    class DiscountType(models.TextChoices):
        PERCENT = "percent", _("Percentage")
        FIXED = "fixed", _("Fixed amount")

    code = models.CharField(max_length=32, unique=True)
    discount_type = models.CharField(max_length=10, choices=DiscountType.choices)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    expiry_date = models.DateTimeField(null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    times_used = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code

    def is_valid(self):
        if not self.is_active:
            return False
        if self.expiry_date and timezone.now() > self.expiry_date:
            return False
        if self.usage_limit is not None and self.times_used >= self.usage_limit:
            return False
        return True
