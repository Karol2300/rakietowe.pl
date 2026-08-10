import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.catalog.models import Brand, Category, Product, ProductVariant, StockNotification
from apps.catalog.services import (
    COMPARE_MAX_ITEMS,
    SORT_OPTIONS,
    annotate_effective_price,
    collect_facets,
    get_compare_ids,
)
from apps.catalog.services import toggle_compare as toggle_compare_service
from apps.reviews.forms import ReviewForm
from apps.reviews.models import Review

PAGE_SIZE = 24


def _paginate(request, queryset):
    paginator = Paginator(queryset, PAGE_SIZE)
    return paginator.get_page(request.GET.get("page"))


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    descendant_categories = category.get_descendants(include_self=True)

    base_products = Product.objects.filter(
        category__in=descendant_categories, is_active=True
    )
    spec_facets, variant_facets = collect_facets(base_products)

    products = annotate_effective_price(base_products).select_related("brand", "category").prefetch_related("variants")

    selected_brands = request.GET.getlist("brand")
    if selected_brands:
        products = products.filter(brand__slug__in=selected_brands)

    min_price = request.GET.get("min_price") or None
    max_price = request.GET.get("max_price") or None
    if min_price:
        products = products.filter(effective_price__gte=min_price)
    if max_price:
        products = products.filter(effective_price__lte=max_price)

    selected_facets = {}
    for key in spec_facets:
        values = request.GET.getlist(key)
        if values:
            products = products.filter(**{f"specs__{key}__in": values})
            selected_facets[key] = values
    for key in variant_facets:
        values = request.GET.getlist(key)
        if values:
            products = products.filter(**{f"variants__attributes__{key}__in": values}).distinct()
            selected_facets[key] = values

    sort = request.GET.get("sort", "newest")
    if sort not in SORT_OPTIONS:
        sort = "newest"
    products = products.order_by(SORT_OPTIONS[sort][0], "-id")

    context = {
        "category": category,
        "brands": Brand.objects.filter(products__in=base_products).distinct().order_by("name"),
        "spec_facets": spec_facets,
        "variant_facets": variant_facets,
        "selected_facets": selected_facets,
        "selected_brands": selected_brands,
        "min_price": min_price,
        "max_price": max_price,
        "sort": sort,
        "sort_options": SORT_OPTIONS,
        "page_obj": _paginate(request, products),
        "result_count": products.count(),
    }
    return render(request, "catalog/category_detail.html", context)


def search(request):
    query = request.GET.get("q", "").strip()
    products = Product.objects.filter(is_active=True)
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query) | Q(brand__name__icontains=query)
        ).distinct()
    products = (
        annotate_effective_price(products)
        .select_related("brand", "category")
        .prefetch_related("variants")
        .order_by("-created_at")
    )

    context = {
        "query": query,
        "page_obj": _paginate(request, products),
        "result_count": products.count(),
    }
    return render(request, "catalog/search_results.html", context)


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related("brand", "category").prefetch_related("variants", "images"),
        slug=slug,
        is_active=True,
    )
    variants = list(product.variants.filter(is_active=True))
    variant_dimension = None
    for variant in variants:
        if variant.attributes:
            variant_dimension = next(iter(variant.attributes))
            break

    default_variant = next((v for v in variants if v.in_stock), variants[0] if variants else None)

    variants_json = json.dumps([
        {
            "id": v.id,
            "attributes": v.attributes,
            "stock": v.stock_quantity,
            "price": str(v.current_price()),
            "sku": v.sku,
        }
        for v in variants
    ])

    related_products = annotate_effective_price(
        Product.objects.filter(category=product.category, is_active=True).exclude(id=product.id)
    ).select_related("brand")[:4]
    if len(related_products) < 4:
        related_products = annotate_effective_price(
            Product.objects.filter(sport=product.sport, is_active=True).exclude(id=product.id)
        ).select_related("brand")[:4]

    reviews = product.reviews.filter(is_visible=True).select_related("user").order_by("-created_at")

    user_review = None
    review_form = None
    if request.user.is_authenticated:
        user_review = Review.objects.filter(product=product, user=request.user).first()
        review_form = ReviewForm(instance=user_review)

    context = {
        "product": product,
        "variants": variants,
        "variant_dimension": variant_dimension,
        "default_variant": default_variant,
        "variants_json": variants_json,
        "related_products": related_products,
        "reviews": reviews,
        "user_review": user_review,
        "review_form": review_form,
        "rating_choices": [5, 4, 3, 2, 1],
    }
    return render(request, "catalog/product_detail.html", context)


@login_required
@require_POST
def request_stock_notification(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id, is_active=True)
    if variant.in_stock:
        messages.info(request, _("That item is already in stock."))
    else:
        _notification, created = StockNotification.objects.get_or_create(user=request.user, variant=variant)
        if created:
            messages.success(request, _("We'll email you when this is back in stock."))
        else:
            messages.info(request, _("You're already on the list for this item."))
    return redirect("catalog:product_detail", slug=variant.product.slug)


@require_POST
def toggle_compare(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    added, capped = toggle_compare_service(request, product.id)
    if capped:
        messages.error(request, _("You can compare up to %(max)s products at a time.") % {"max": COMPARE_MAX_ITEMS})
    elif added:
        messages.success(request, _("Added %(name)s to comparison.") % {"name": product.name})
    else:
        messages.success(request, _("Removed %(name)s from comparison.") % {"name": product.name})
    return redirect(request.META.get("HTTP_REFERER") or reverse("catalog:product_detail", args=[slug]))


def compare_view(request):
    ids = get_compare_ids(request)
    products = list(
        annotate_effective_price(Product.objects.filter(id__in=ids))
        .select_related("brand")
        .prefetch_related("variants")
    )
    products.sort(key=lambda p: ids.index(p.id))

    spec_keys = []
    for product in products:
        for key in product.specs:
            if key not in spec_keys:
                spec_keys.append(key)

    rows = [(key, [product.specs.get(key, "—") for product in products]) for key in spec_keys]

    return render(request, "catalog/compare.html", {"products": products, "rows": rows})


def search_suggestions(request):
    query = request.GET.get("q", "").strip()
    results = []
    if len(query) >= 2:
        products = (
            Product.objects.filter(is_active=True, name__icontains=query)
            .select_related("brand")
            .order_by("-review_count")[:8]
        )
        for product in products:
            results.append({
                "name": product.name,
                "brand": product.brand.name if product.brand else "",
                "search_url": f"{reverse('catalog:search')}?q={product.name}",
            })
    return JsonResponse({"results": results})
