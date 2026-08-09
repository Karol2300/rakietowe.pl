from django.contrib import admin
from mptt.admin import MPTTModelAdmin

from .models import Brand, Category, PriceHistory, Product, ProductImage, ProductVariant, StockNotification

admin.site.register(Category, MPTTModelAdmin)
admin.site.register(Brand)
admin.site.register(Product)
admin.site.register(ProductImage)
admin.site.register(ProductVariant)
admin.site.register(PriceHistory)
admin.site.register(StockNotification)
