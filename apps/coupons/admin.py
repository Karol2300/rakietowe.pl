from django.contrib import admin

from .models import Coupon


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_type", "value", "times_used", "usage_limit", "expiry_date", "is_active")
    list_filter = ("discount_type", "is_active")
    search_fields = ("code",)
