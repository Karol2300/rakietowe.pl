import uuid

from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from mptt.models import MPTTModel, TreeForeignKey


class Sport(models.TextChoices):
    TENNIS = "tennis", _("Tennis")
    SQUASH = "squash", _("Squash")
    BADMINTON = "badminton", _("Badminton")
    TABLE_TENNIS = "table_tennis", _("Table Tennis")


class Category(MPTTModel):
    """Sport -> product type -> sub-type tree, drives nav + listing filters."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=140, unique=True)
    parent = TreeForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="categories/", blank=True)
    is_active = models.BooleanField(default=True)

    class MPTTMeta:
        order_insertion_by = ["name"]

    class Meta:
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    logo = models.ImageField(upload_to="brands/", blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True)
    description = models.TextField(blank=True)

    sport = models.CharField(max_length=20, choices=Sport.choices)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )
    brand = models.ForeignKey(
        Brand, on_delete=models.PROTECT, related_name="products", null=True, blank=True
    )

    price_pln = models.DecimalField(max_digits=10, decimal_places=2)
    price_eur = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_usd = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    sale_price_pln = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sale_price_eur = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sale_price_usd = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sale_start = models.DateTimeField(null=True, blank=True)
    sale_end = models.DateTimeField(null=True, blank=True)

    specs = models.JSONField(
        default=dict,
        blank=True,
        help_text="Sport-specific spec table, e.g. {'weight_g': 300, 'head_size_sq_in': 100}",
    )

    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    review_count = models.PositiveIntegerField(default=0)

    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.CharField(max_length=500, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["sport"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def is_on_sale(self, now=None):
        from django.utils import timezone

        now = now or timezone.now()
        if self.sale_price_pln is None:
            return False
        if self.sale_start and now < self.sale_start:
            return False
        if self.sale_end and now > self.sale_end:
            return False
        return True

    def current_price(self, currency="PLN"):
        currency = currency.upper()
        on_sale = self.is_on_sale()
        field = f"{'sale_price' if on_sale else 'price'}_{currency.lower()}"
        return getattr(self, field, None) or self.price_pln


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/")
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    ordering = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordering", "id"]


def generate_sku(product, attributes):
    parts = [
        product.sport[:3],
        product.category.slug[:3],
        (product.brand.slug[:3] if product.brand else "gen"),
    ]
    for value in attributes.values():
        parts.append(str(value)[:3])
    base = "-".join(p.upper() for p in parts if p)
    return f"{base}-{uuid.uuid4().hex[:6].upper()}"


class ProductVariant(models.Model):
    """The purchasable unit: has its own stock/SKU and optional price override."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField(max_length=64, unique=True, blank=True)
    attributes = models.JSONField(default=dict, blank=True)

    price_pln_override = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_eur_override = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_usd_override = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    stock_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        attrs = ", ".join(f"{k}={v}" for k, v in self.attributes.items())
        return f"{self.product.name} ({attrs})" if attrs else f"{self.product.name} ({self.sku})"

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = generate_sku(self.product, self.attributes)
        super().save(*args, **kwargs)

    def current_price(self, currency="PLN"):
        currency = currency.upper()
        override = getattr(self, f"price_{currency.lower()}_override", None)
        return override if override is not None else self.product.current_price(currency)

    @property
    def in_stock(self):
        return self.stock_quantity > 0


class PriceHistory(models.Model):
    class PriceType(models.TextChoices):
        REGULAR = "regular", _("Regular price")
        SALE = "sale", _("Sale price")

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="price_history", null=True, blank=True
    )
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE, related_name="price_history", null=True, blank=True
    )
    price_type = models.CharField(max_length=10, choices=PriceType.choices, default=PriceType.REGULAR)
    currency = models.CharField(max_length=3, default="PLN")
    old_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    new_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "price history"
        ordering = ["-changed_at"]

    def __str__(self):
        target = self.variant or self.product
        return f"{target}: {self.old_price} -> {self.new_price} {self.currency}"


class StockNotification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="stock_notifications"
    )
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE, related_name="notification_requests"
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    notified = models.BooleanField(default=False)
    notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "variant")
