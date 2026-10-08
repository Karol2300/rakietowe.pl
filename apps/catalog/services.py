import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Case, DecimalField, F, Q, Value, When
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


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


OMNIBUS_LOOKBACK_DAYS = 30


def bulk_lowest_price_30d(products):
    """Polish/EU Omnibus directive: whenever a reduced price is shown, the
    lowest price charged in the 30 days before the reduction must be shown
    alongside it. Returns {product_id: Decimal} for products currently on
    sale, using PriceHistory (regular-price edits + logged sale windows) as
    the source of truth. Batched into two queries regardless of page size,
    so it's safe to call from listing views with many products.
    """
    from .models import PriceHistory

    products = list(products)
    ids = [p.id for p in products if p.is_on_sale()]
    if not ids:
        return {}

    now = timezone.now()
    window_start = now - timedelta(days=OMNIBUS_LOOKBACK_DAYS)
    lowest = {p.id: p.price_pln for p in products if p.id in ids}

    regular_entries = PriceHistory.objects.filter(
        product_id__in=ids, price_type=PriceHistory.PriceType.REGULAR, changed_at__gte=window_start
    ).values_list("product_id", "old_price", "new_price")
    for product_id, old_price, new_price in regular_entries:
        for price in (old_price, new_price):
            if price is not None and price < lowest[product_id]:
                lowest[product_id] = price

    # Only *past, already-ended* promos count as reference prices here - the
    # currently active sale (sale_end null-or-future) must never be counted
    # against itself, or the "lowest price" would just echo the sale price.
    # This assumes past promos were logged with a real sale_end; an
    # open-ended promo that got silently replaced by a new one without ever
    # setting an end date won't be picked up - an acceptable gap for how
    # promotions are actually configured here.
    sale_entries = (
        PriceHistory.objects.filter(
            product_id__in=ids,
            price_type=PriceHistory.PriceType.SALE,
            new_price__isnull=False,
            sale_end__isnull=False,
            sale_end__gte=window_start,
            sale_end__lt=now,
        )
        .values_list("product_id", "new_price")
    )
    for product_id, new_price in sale_entries:
        if new_price < lowest[product_id]:
            lowest[product_id] = new_price

    return lowest


def attach_lowest_price_30d(products):
    """Set `.lowest_price_30d` on each on-sale product in `products` (a list
    or already-evaluated iterable). Call this after pagination/slicing so
    it only runs against the products actually being rendered."""
    products = list(products)
    lowest_by_id = bulk_lowest_price_30d(products)
    for product in products:
        product.lowest_price_30d = lowest_by_id.get(product.id)
    return products


SORT_OPTIONS = {
    "newest": ("-created_at", _("Newest")),
    "price_asc": ("effective_price", _("Price: low to high")),
    "price_desc": ("-effective_price", _("Price: high to low")),
    "rating": ("-average_rating", _("Top rated")),
    "popularity": ("-review_count", _("Most popular")),
}


def _spec_value_text(value):
    """Match PostgreSQL's JSONB ->> ("get as text") representation, since
    category_detail() filters specs via KeyTextTransform against this same
    text form. Values in Product.specs can be ints, floats, or bools (the
    admin's specs widget and the seed script both store typed JSON, not
    just strings) - str() alone would render True as "True" instead of
    the "true" Postgres/JSON produces, so a boolean facet checkbox would
    never actually match its own filter."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def collect_facets(products_queryset):
    """Build filter facets from Product.specs and ProductVariant.attributes
    across the given (unfiltered-by-facet) product queryset."""
    from apps.catalog.models import ProductVariant

    spec_facets = {}
    for specs in products_queryset.values_list("specs", flat=True):
        for key, value in (specs or {}).items():
            spec_facets.setdefault(key, set()).add(_spec_value_text(value))

    variant_facets = {}
    variants = ProductVariant.objects.filter(product__in=products_queryset, is_active=True)
    for attrs in variants.values_list("attributes", flat=True):
        for key, value in (attrs or {}).items():
            variant_facets.setdefault(key, set()).add(value)

    return (
        {k: sorted(v, key=str) for k, v in spec_facets.items()},
        {k: sorted(v, key=str) for k, v in variant_facets.items()},
    )


def notify_back_in_stock(variant):
    """Email everyone waiting on this variant, then mark them notified.
    Called from ProductVariant.save() when stock goes from 0 to positive."""
    pending = variant.notification_requests.filter(notified=False).select_related("user")
    if not pending.exists():
        return

    subject = f"Back in stock: {variant.product.name} - Racket Sports Shop"
    for notification in pending:
        message = render_to_string(
            "catalog/email/back_in_stock.txt",
            {"notification": notification, "product": variant.product, "variant": variant},
        )
        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [notification.user.email])
        except Exception:
            # Never let a mail failure (SMTP down, encoding issue, etc.) break
            # the stock save this is triggered from. Leave notified=False so
            # this person is retried on the next restock.
            logger.exception("Failed to send back-in-stock email to %s", notification.user.email)
            continue
        notification.notified = True
        notification.notified_at = timezone.now()
        notification.save(update_fields=["notified", "notified_at"])


COMPARE_SESSION_KEY = "compare_product_ids"
COMPARE_MAX_ITEMS = 4


def get_compare_ids(request):
    return request.session.get(COMPARE_SESSION_KEY, [])


def toggle_compare(request, product_id):
    """Returns (is_now_in_list, was_capped)."""
    ids = get_compare_ids(request)
    product_id = int(product_id)
    if product_id in ids:
        ids.remove(product_id)
        added = False
        capped = False
    elif len(ids) >= COMPARE_MAX_ITEMS:
        added = False
        capped = True
    else:
        ids.append(product_id)
        added = True
        capped = False
    request.session[COMPARE_SESSION_KEY] = ids
    return added, capped


def remove_from_compare(request, product_id):
    ids = get_compare_ids(request)
    product_id = int(product_id)
    if product_id in ids:
        ids.remove(product_id)
        request.session[COMPARE_SESSION_KEY] = ids
