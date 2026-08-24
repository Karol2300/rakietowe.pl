from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

# Two admin tiers, on top of Django's own is_staff/is_superuser:
#   Staff       - day-to-day catalog upkeep and order fulfillment.
#   Store Admin - Staff's permissions plus coupons, loyalty, shipping
#                 config and customer account management.
# Superusers are unrestricted by design and aren't part of either group -
# only a superuser can grant permissions or manage other staff accounts
# (auth.group / auth.permission are deliberately never granted here).
STAFF_PERMISSIONS = {
    "catalog": {
        "Product": ["view", "add", "change"],
        "ProductVariant": ["view", "add", "change"],
        "ProductImage": ["view", "add", "change", "delete"],
        "Category": ["view"],
        "Brand": ["view"],
        "StockNotification": ["view"],
        "PriceHistory": ["view"],
    },
    "orders": {
        "Order": ["view", "change"],
        "OrderItem": ["view"],
        "ReturnRequest": ["view", "change"],
        "Invoice": ["view"],
    },
    "reviews": {
        "Review": ["view", "change", "delete"],
    },
}

STORE_ADMIN_EXTRA_PERMISSIONS = {
    "catalog": {
        "Product": ["delete"],
        "ProductVariant": ["delete"],
        "Category": ["add", "change", "delete"],
        "Brand": ["add", "change", "delete"],
    },
    "orders": {
        "Order": ["add", "delete"],
        "ReturnRequest": ["delete"],
    },
    "coupons": {
        "Coupon": ["view", "add", "change", "delete"],
    },
    "loyalty": {
        "LoyaltyAccount": ["view", "add", "change", "delete"],
        "LoyaltyTransaction": ["view", "add", "change", "delete"],
    },
    "shipping": {
        "ShippingMethod": ["view", "add", "change", "delete"],
    },
    "accounts": {
        "User": ["view", "change"],
        "Address": ["view", "change", "delete"],
    },
}


def _resolve_permissions(spec):
    perms = []
    for app_label, models in spec.items():
        for model_name, actions in models.items():
            content_type = ContentType.objects.get(app_label=app_label, model=model_name.lower())
            for action in actions:
                perms.append(Permission.objects.get(content_type=content_type, codename=f"{action}_{model_name.lower()}"))
    return perms


def _merge(*specs):
    merged = {}
    for spec in specs:
        for app_label, models in spec.items():
            merged.setdefault(app_label, {})
            for model_name, actions in models.items():
                merged[app_label].setdefault(model_name, [])
                for action in actions:
                    if action not in merged[app_label][model_name]:
                        merged[app_label][model_name].append(action)
    return merged


class Command(BaseCommand):
    help = "Create/update the Staff and Store Admin groups with their permission sets. Safe to re-run."

    def handle(self, *args, **options):
        staff_group, _ = Group.objects.get_or_create(name="Staff")
        staff_group.permissions.set(_resolve_permissions(STAFF_PERMISSIONS))

        store_admin_group, _ = Group.objects.get_or_create(name="Store Admin")
        store_admin_group.permissions.set(
            _resolve_permissions(_merge(STAFF_PERMISSIONS, STORE_ADMIN_EXTRA_PERMISSIONS))
        )

        self.stdout.write(self.style.SUCCESS(
            f"Staff: {staff_group.permissions.count()} permissions. "
            f"Store Admin: {store_admin_group.permissions.count()} permissions."
        ))
