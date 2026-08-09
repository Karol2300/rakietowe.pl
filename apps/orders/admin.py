from django.contrib import admin

from .models import Invoice, Order, OrderItem, ReturnRequest


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "user", "status", "payment_status", "total", "created_at")
    list_filter = ("status", "payment_status", "carrier")
    search_fields = ("order_number", "guest_email", "user__email")
    inlines = [OrderItemInline]


admin.site.register(Invoice)
admin.site.register(ReturnRequest)
