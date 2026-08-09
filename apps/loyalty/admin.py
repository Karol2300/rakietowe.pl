from django.contrib import admin

from .models import LoyaltyAccount, LoyaltyTransaction

admin.site.register(LoyaltyAccount)
admin.site.register(LoyaltyTransaction)
