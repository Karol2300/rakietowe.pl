from django.db import models
from django.utils.translation import gettext_lazy as _


class Carrier(models.TextChoices):
    INPOST = "inpost", _("InPost Parcel Locker")
    DHL = "dhl", _("DHL")
    DPD = "dpd", _("DPD")
    UPS = "ups", _("UPS")


class ShippingMethod(models.Model):
    carrier = models.CharField(max_length=10, choices=Carrier.choices)
    name = models.CharField(max_length=100)
    is_flat_rate = models.BooleanField(default=True)
    flat_rate_pln = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    cost_per_kg_pln = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    free_shipping_threshold_pln = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    estimated_days_min = models.PositiveSmallIntegerField(default=1)
    estimated_days_max = models.PositiveSmallIntegerField(default=3)
    requires_locker_selection = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["flat_rate_pln"]

    def __str__(self):
        return f"{self.get_carrier_display()} - {self.name}"

    def cost_for(self, order_total_pln, weight_kg=0):
        if self.free_shipping_threshold_pln and order_total_pln >= self.free_shipping_threshold_pln:
            return 0
        if self.is_flat_rate:
            return self.flat_rate_pln or 0
        return (self.cost_per_kg_pln or 0) * weight_kg
