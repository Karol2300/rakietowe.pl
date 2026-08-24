from itertools import chain

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import render

from apps.catalog.models import Product
from apps.catalog.services import annotate_effective_price, attach_lowest_price_30d

FEATURED_PRODUCTS_CACHE_KEY = "home_featured_products"
FEATURED_PRODUCTS_CACHE_SECONDS = 300


def _load_featured_products():
    base = annotate_effective_price(
        Product.objects.filter(is_active=True).select_related("brand", "category").prefetch_related("variants")
    )
    on_sale = list(base.filter(on_sale=True).order_by("-created_at")[:8])
    if len(on_sale) < 8:
        fillers = base.exclude(id__in=[p.id for p in on_sale]).order_by("-average_rating", "-review_count")
        on_sale = list(chain(on_sale, fillers[: 8 - len(on_sale)]))
    attach_lowest_price_30d(on_sale)
    return on_sale


def home(request):
    # The homepage is the highest-traffic page and this product list is the
    # same for every visitor (per-user state like compare/cart membership is
    # applied separately at render time), so it's cached rather than
    # recomputed - including the extra PriceHistory queries from
    # attach_lowest_price_30d - on every single request.
    featured_products = cache.get_or_set(
        FEATURED_PRODUCTS_CACHE_KEY, _load_featured_products, FEATURED_PRODUCTS_CACHE_SECONDS
    )
    return render(request, "core/home.html", {"featured_products": featured_products})


def _store_context():
    return {
        "store_legal_name": settings.STORE_LEGAL_NAME,
        "store_vat_id": settings.STORE_VAT_ID,
        "store_address_line": settings.STORE_ADDRESS_LINE,
        "store_city_line": settings.STORE_CITY_LINE,
        "contact_email": settings.PRIVACY_CONTACT_EMAIL,
    }


def privacy_policy(request):
    return render(request, "core/privacy_policy.html", _store_context())


def terms(request):
    return render(request, "core/terms.html", _store_context())


def robots_txt(request):
    # Content lives under a required /en/ or /pl/ prefix (see
    # config/urls.py's i18n_patterns), so private paths need disallowing
    # under both language prefixes - a bare "/accounts/" wouldn't match
    # "/en/accounts/...".
    private_paths = ["accounts", "cart", "checkout", "account"]
    lines = ["User-agent: *", "Disallow: /admin/"]
    for lang_code, _label in settings.LANGUAGES:
        for path in private_paths:
            lines.append(f"Disallow: /{lang_code}/{path}/")
    lines += ["Disallow: /webhooks/", "", f"Sitemap: {request.scheme}://{request.get_host()}/sitemap.xml"]
    return HttpResponse("\n".join(lines), content_type="text/plain")
