import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Case, DecimalField, F, Q, Value, When
from django.template.loader import render_to_string
from django.utils import timezone

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

    pending.update(notified=True, notified_at=timezone.now())


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
