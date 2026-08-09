from django.db.models import Case, DecimalField, F, Q, Value, When
from django.utils import timezone


def annotate_effective_price(queryset):
    """Annotate each product with `effective_price`: the sale price if a
    scheduled sale is currently active, otherwise the regular price."""
    now = timezone.now()
    on_sale_condition = (
        Q(sale_price_pln__isnull=False)
        & (Q(sale_start__isnull=True) | Q(sale_start__lte=now))
        & (Q(sale_end__isnull=True) | Q(sale_end__gte=now))
    )
    return queryset.annotate(
        effective_price=Case(
            When(on_sale_condition, then=F("sale_price_pln")),
            default=F("price_pln"),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        ),
        on_sale=Case(
            When(on_sale_condition, then=Value(True)),
            default=Value(False),
        ),
    )


SORT_OPTIONS = {
    "newest": ("-created_at", "Newest"),
    "price_asc": ("effective_price", "Price: low to high"),
    "price_desc": ("-effective_price", "Price: high to low"),
    "rating": ("-average_rating", "Top rated"),
    "popularity": ("-review_count", "Most popular"),
}


def collect_facets(products_queryset):
    """Build filter facets from Product.specs and ProductVariant.attributes
    across the given (unfiltered-by-facet) product queryset."""
    from apps.catalog.models import ProductVariant

    spec_facets = {}
    for specs in products_queryset.values_list("specs", flat=True):
        for key, value in (specs or {}).items():
            spec_facets.setdefault(key, set()).add(value)

    variant_facets = {}
    variants = ProductVariant.objects.filter(product__in=products_queryset, is_active=True)
    for attrs in variants.values_list("attributes", flat=True):
        for key, value in (attrs or {}).items():
            variant_facets.setdefault(key, set()).add(value)

    return (
        {k: sorted(v, key=str) for k, v in spec_facets.items()},
        {k: sorted(v, key=str) for k, v in variant_facets.items()},
    )
