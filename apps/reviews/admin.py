from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "verified_purchase", "is_visible", "created_at")
    list_filter = ("rating", "verified_purchase", "is_visible")
    search_fields = ("product__name", "user__email", "comment")
