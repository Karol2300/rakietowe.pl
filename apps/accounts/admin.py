from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Address, User

admin.site.register(User, UserAdmin)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("full_name", "user", "city", "country", "is_default")
    list_filter = ("country", "is_default")
    search_fields = ("full_name", "user__email", "city", "postal_code")
