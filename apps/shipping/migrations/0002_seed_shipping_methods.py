from django.db import migrations


METHODS = [
    dict(carrier="inpost", name="InPost Parcel Locker", is_flat_rate=True, flat_rate_pln=12.99,
         free_shipping_threshold_pln=250, estimated_days_min=1, estimated_days_max=2,
         requires_locker_selection=True),
    dict(carrier="dpd", name="DPD Courier", is_flat_rate=True, flat_rate_pln=16.99,
         free_shipping_threshold_pln=300, estimated_days_min=1, estimated_days_max=3),
    dict(carrier="dhl", name="DHL Courier", is_flat_rate=True, flat_rate_pln=18.99,
         free_shipping_threshold_pln=300, estimated_days_min=1, estimated_days_max=3),
    dict(carrier="ups", name="UPS Standard", is_flat_rate=True, flat_rate_pln=24.99,
         free_shipping_threshold_pln=350, estimated_days_min=2, estimated_days_max=5),
]


def seed_shipping_methods(apps, schema_editor):
    ShippingMethod = apps.get_model("shipping", "ShippingMethod")
    for data in METHODS:
        ShippingMethod.objects.get_or_create(carrier=data["carrier"], name=data["name"], defaults=data)


def remove_shipping_methods(apps, schema_editor):
    ShippingMethod = apps.get_model("shipping", "ShippingMethod")
    ShippingMethod.objects.filter(carrier__in=[m["carrier"] for m in METHODS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("shipping", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_shipping_methods, remove_shipping_methods),
    ]
