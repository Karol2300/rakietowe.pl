from django.contrib import admin

from .models import ShippingMethod


@admin.register(ShippingMethod)
class ShippingMethodAdmin(admin.ModelAdmin):
    list_display = ("name", "carrier", "is_flat_rate", "flat_rate_pln", "estimated_days_min", "estimated_days_max", "is_active")
    list_filter = ("carrier", "is_active")
