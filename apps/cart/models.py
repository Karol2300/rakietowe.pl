from django.conf import settings
from django.db import models

from apps.catalog.models import Product, ProductVariant


class Cart(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="carts"
    )
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart({self.user or self.session_key})"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="cart_items")
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("cart", "variant")

    @property
    def line_total(self):
        return self.variant.current_price() * self.quantity


class Wishlist(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist")

    def __str__(self):
        return f"Wishlist({self.user})"


class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="wishlisted_by")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("wishlist", "product")
