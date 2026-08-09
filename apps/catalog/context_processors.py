from apps.catalog.models import Category


def sport_navigation(request):
    roots = Category.objects.filter(parent__isnull=True, is_active=True).order_by("tree_id")
    return {"sport_nav_categories": roots}
