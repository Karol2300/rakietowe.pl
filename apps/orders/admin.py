from django.contrib import admin, messages

from .models import Invoice, Order, OrderItem, ReturnRequest
from .services import mark_cancelled, mark_delivered, mark_shipped, process_return_refund, update_return_status


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.action(description="Mark selected orders as shipped (uses the Tracking number already saved on the order)")
def action_mark_shipped(modeladmin, request, queryset):
    count = 0
    for order in queryset.filter(payment_status=Order.PaymentStatus.PAID):
        mark_shipped(order, tracking_number=order.tracking_number)
        count += 1
    modeladmin.message_user(request, f"Marked {count} order(s) as shipped.", messages.SUCCESS)


@admin.action(description="Mark selected orders as delivered")
def action_mark_delivered(modeladmin, request, queryset):
    count = 0
    for order in queryset.filter(status=Order.Status.SHIPPED):
        mark_delivered(order)
        count += 1
    modeladmin.message_user(request, f"Marked {count} order(s) as delivered.", messages.SUCCESS)


@admin.action(description="Cancel selected orders (refunds automatically if already paid)")
def action_mark_cancelled(modeladmin, request, queryset):
    count = 0
    for order in queryset.exclude(status__in=[Order.Status.CANCELLED, Order.Status.DELIVERED]):
        mark_cancelled(order)
        count += 1
    modeladmin.message_user(request, f"Cancelled {count} order(s).", messages.SUCCESS)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "user", "status", "payment_status", "total", "created_at")
    list_filter = ("status", "payment_status", "carrier")
    search_fields = ("order_number", "guest_email", "user__email")
    inlines = [OrderItemInline]
    actions = [action_mark_shipped, action_mark_delivered, action_mark_cancelled]


@admin.action(description="Approve selected return requests")
def action_approve_returns(modeladmin, request, queryset):
    count = 0
    for rr in queryset.filter(status=ReturnRequest.Status.REQUESTED):
        update_return_status(rr, ReturnRequest.Status.APPROVED)
        count += 1
    modeladmin.message_user(request, f"Approved {count} return request(s).", messages.SUCCESS)


@admin.action(description="Reject selected return requests")
def action_reject_returns(modeladmin, request, queryset):
    count = 0
    for rr in queryset.filter(status=ReturnRequest.Status.REQUESTED):
        update_return_status(rr, ReturnRequest.Status.REJECTED)
        count += 1
    modeladmin.message_user(request, f"Rejected {count} return request(s).", messages.SUCCESS)


@admin.action(description="Refund selected (approved) return requests")
def action_refund_returns(modeladmin, request, queryset):
    count = 0
    for rr in queryset.filter(status=ReturnRequest.Status.APPROVED):
        process_return_refund(rr)
        count += 1
    modeladmin.message_user(request, f"Refunded {count} return request(s).", messages.SUCCESS)


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = ("order", "item", "quantity", "status", "created_at")
    list_filter = ("status",)
    actions = [action_approve_returns, action_reject_returns, action_refund_returns]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "order", "issued_at")
    search_fields = ("invoice_number", "order__order_number")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
