from django.core.cache import cache

from apps.catalog.models import Category, Sport
from apps.catalog.services import get_compare_ids

# Root categories are named after their sport (see seed_products.create_categories),
# but MPTT's order_insertion_by=["name"] sorts siblings alphabetically at
# insert time, so the tree_id order doesn't match Sport.choices. Re-sort here
# to the declared Sport order (Tennis, Squash, Badminton, Table Tennis)
# instead of touching MPTT ordering, which also governs sub-category order.
_SPORT_NAV_ORDER = {label: index for index, (_, label) in enumerate(Sport.choices)}

SPORT_NAV_CACHE_KEY = "sport_nav_categories"
SPORT_NAV_CACHE_SECONDS = 900


def sport_navigation(request):
    # Runs on every page load; the result is identical for every visitor
    # (category names aren't per-locale) so it's cached rather than hitting
    # the DB on every request. A 15-minute TTL means admin changes to the
    # top-level category tree take up to that long to show up in the nav.
    roots = cache.get(SPORT_NAV_CACHE_KEY)
    if roots is None:
        roots = list(Category.objects.filter(parent__isnull=True, is_active=True))
        roots = sorted(roots, key=lambda c: _SPORT_NAV_ORDER.get(c.name, len(_SPORT_NAV_ORDER)))
        cache.set(SPORT_NAV_CACHE_KEY, roots, SPORT_NAV_CACHE_SECONDS)
    return {"sport_nav_categories": roots}


def compare_summary(request):
    ids = get_compare_ids(request)
    return {"compare_count": len(ids), "compare_ids": ids}
