from django.contrib import admin

from .models import LoyaltyAccount, LoyaltyTransaction


class LoyaltyTransactionInline(admin.TabularInline):
    model = LoyaltyTransaction
    extra = 0
    readonly_fields = ("kind", "points", "order", "created_at")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(LoyaltyAccount)
class LoyaltyAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "points_balance")
    search_fields = ("user__email",)
    inlines = [LoyaltyTransactionInline]


@admin.register(LoyaltyTransaction)
class LoyaltyTransactionAdmin(admin.ModelAdmin):
    list_display = ("account", "kind", "points", "order", "created_at")
    list_filter = ("kind",)
    search_fields = ("account__user__email",)
