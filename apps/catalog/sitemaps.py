from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Category, Product


class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8
    i18n = True
    alternates = True

    def items(self):
        return Product.objects.filter(is_active=True).order_by("id")

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse("catalog:product_detail", args=[obj.slug])


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6
    i18n = True
    alternates = True

    def items(self):
        return Category.objects.filter(is_active=True).order_by("id")

    def location(self, obj):
        return reverse("catalog:category_detail", args=[obj.slug])
