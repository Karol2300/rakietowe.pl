import csv
import io
from decimal import Decimal, InvalidOperation

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import path
from django.utils.dateparse import parse_datetime
from mptt.admin import MPTTModelAdmin

from .admin_widgets import SpecsWidget
from .models import Brand, Category, PriceHistory, Product, ProductImage, ProductVariant, StockNotification

PRICE_IMPORT_DECIMAL_FIELDS = [
    "price_pln", "price_eur", "price_usd",
    "sale_price_pln", "sale_price_eur", "sale_price_usd",
]
PRICE_IMPORT_DATETIME_FIELDS = ["sale_start", "sale_end"]


@admin.action(description="Export selected products' prices to CSV")
def export_prices_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="product_prices.csv"'
    writer = csv.writer(response)
    writer.writerow([
        "slug", "name", "price_pln", "price_eur", "price_usd",
        "sale_price_pln", "sale_price_eur", "sale_price_usd",
        "sale_start", "sale_end", "vat_rate",
    ])
    for product in queryset.order_by("name"):
        writer.writerow([
            product.slug,
            product.name,
            product.price_pln,
            product.price_eur or "",
            product.price_usd or "",
            product.sale_price_pln or "",
            product.sale_price_eur or "",
            product.sale_price_usd or "",
            product.sale_start.isoformat() if product.sale_start else "",
            product.sale_end.isoformat() if product.sale_end else "",
            product.vat_rate,
        ])
    return response


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ("sku", "attributes", "stock_quantity", "price_pln_override", "is_active")


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0


class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = "__all__"
        widgets = {"specs": SpecsWidget}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = ("name", "brand", "sport", "price_pln", "vat_rate", "total_stock", "is_active")
    list_filter = ("sport", "vat_rate", "is_active", "brand")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductVariantInline, ProductImageInline]
    actions = [export_prices_csv]

    def save_model(self, request, obj, form, change):
        # Threads the editing user through to Product.save() so the
        # PriceHistory entries it logs record who changed the price.
        obj._price_change_user = request.user
        super().save_model(request, obj, form, change)

    def get_urls(self):
        custom = [
            path(
                "import-prices/",
                self.admin_site.admin_view(self.import_prices_view),
                name="catalog_product_import_prices",
            ),
        ]
        return custom + super().get_urls()

    def import_prices_view(self, request):
        if not self.has_change_permission(request):
            raise PermissionDenied

        if request.method == "POST" and request.FILES.get("csv_file"):
            updated, errors = self._import_prices(request, request.FILES["csv_file"])
            if updated:
                messages.success(request, f"Updated prices for {updated} product(s).")
            for error in errors[:20]:
                messages.error(request, error)
            if len(errors) > 20:
                messages.error(request, f"...and {len(errors) - 20} more error(s).")
            if not updated and not errors:
                messages.warning(request, "The CSV had no data rows.")
            return redirect("admin:catalog_product_changelist")

        context = {
            **self.admin_site.each_context(request),
            "title": "Import product prices (CSV)",
            "opts": self.model._meta,
        }
        return render(request, "admin/catalog/product_import_prices.html", context)

    def _import_prices(self, request, uploaded_file):
        """Update existing products' prices from an uploaded CSV, matched by
        slug. Never creates products. Blank cells leave that field
        unchanged. Every change goes through Product.save(), so it's logged
        to PriceHistory exactly like an admin form edit."""
        decoded = io.TextIOWrapper(uploaded_file.file, encoding="utf-8-sig")
        reader = csv.DictReader(decoded)
        updated = 0
        errors = []
        for line_number, row in enumerate(reader, start=2):
            slug = (row.get("slug") or "").strip()
            if not slug:
                errors.append(f"Row {line_number}: missing slug, skipped.")
                continue
            try:
                product = Product.objects.get(slug=slug)
            except Product.DoesNotExist:
                errors.append(f"Row {line_number}: no product with slug '{slug}', skipped.")
                continue

            try:
                for field in PRICE_IMPORT_DECIMAL_FIELDS:
                    raw = (row.get(field) or "").strip()
                    if raw:
                        setattr(product, field, Decimal(raw))
                for field in PRICE_IMPORT_DATETIME_FIELDS:
                    raw = (row.get(field) or "").strip()
                    if raw:
                        parsed = parse_datetime(raw)
                        if parsed is None:
                            raise ValueError(f"unrecognized {field} '{raw}'")
                        setattr(product, field, parsed)
            except (InvalidOperation, ValueError) as exc:
                errors.append(f"Row {line_number} ({slug}): {exc}")
                continue

            product._price_change_user = request.user
            product.save()
            updated += 1
        return updated, errors


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ("product", "variant", "price_type", "old_price", "new_price", "currency", "changed_by", "changed_at")
    list_filter = ("price_type", "currency")
    readonly_fields = [f.name for f in PriceHistory._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("sku", "product", "stock_quantity", "in_stock", "is_active")
    list_filter = ("is_active",)
    search_fields = ("sku", "product__name")


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(StockNotification)
class StockNotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "variant", "requested_at", "notified", "notified_at")
    list_filter = ("notified",)
    search_fields = ("user__email", "variant__sku")


@admin.register(Category)
class CategoryAdmin(MPTTModelAdmin):
    prepopulated_fields = {"slug": ("name",)}


admin.site.register(ProductImage)
