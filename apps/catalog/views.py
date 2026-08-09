from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from apps.catalog.models import Brand, Category, Product
from apps.catalog.services import SORT_OPTIONS, annotate_effective_price, collect_facets

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
