from apps.catalog.models import Category
from apps.catalog.services import get_compare_ids


def sport_navigation(request):
    roots = Category.objects.filter(parent__isnull=True, is_active=True).order_by("tree_id")
    return {"sport_nav_categories": roots}


def compare_summary(request):
    ids = get_compare_ids(request)
    return {"compare_count": len(ids), "compare_ids": ids}
