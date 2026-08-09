from itertools import chain

from django.shortcuts import render

from apps.catalog.models import Product
from apps.catalog.services import annotate_effective_price


def home(request):
    base = annotate_effective_price(
        Product.objects.filter(is_active=True).select_related("brand", "category").prefetch_related("variants")
    )
    on_sale = list(base.filter(on_sale=True).order_by("-created_at")[:8])
    if len(on_sale) < 8:
        fillers = base.exclude(id__in=[p.id for p in on_sale]).order_by("-average_rating", "-review_count")
        on_sale = list(chain(on_sale, fillers[: 8 - len(on_sale)]))

    return render(request, "core/home.html", {"featured_products": on_sale})
