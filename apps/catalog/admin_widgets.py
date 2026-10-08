import json

from django import forms

from .specs import SPEC_LABELS

# The fixed vocabulary of spec keys used across the catalog (see
# seed_products.specs_for for the full per-product-kind picture). Keeping
# this as a flat dropdown - rather than one list per product kind - avoids
# needing a "kind" concept on Product itself, which doesn't otherwise exist.
SPEC_KEY_CHOICES = [(key, SPEC_LABELS[key]) for key in (
    "weight_g",
    "balance_point_mm",
    "stiffness_ra",
    "head_size_sq_in",
    "string_pattern",
    "flex",
    "balance",
    "blade_material",
    "speed_rating",
    "spin_rating",
    "control_rating",
    "handle_type",
    "sponge_thickness_mm",
    "speed",
    "spin",
    "control",
    "gauge_mm",
    "material",
    "recommended_tension_lbs",
    "pack_size",
    "capacity_l",
    "compartments",
    "upper_material",
    "sole_type",
    "fit",
    "lens_type",
    "uv_protection",
    "thickness_mm",
    "foldable",
    "indoor_outdoor",
)]


def _coerce_value(raw):
    """The text input is always a plain string, but specs are stored as
    typed JSON values (seed data uses real ints/floats/bools for things
    like weight_g or uv_protection) - PostgreSQL's JSONB lookups are
    type-strict, so a facet filter querying weight_g=260 (int) silently
    misses products where the same value was saved as the string "260".
    Coercing here keeps values saved through this widget consistent with
    everything else already in the catalog, including re-saving an
    untouched product's existing specs."""
    if raw.lower() in ("true", "false"):
        return raw.lower() == "true"
    for cast in (int, float):
        try:
            return cast(raw)
        except ValueError:
            continue
    return raw


class SpecsWidget(forms.Widget):
    """Renders a JSONField storing a flat {key: value} dict as repeatable
    (dropdown key, text value) rows instead of a raw JSON textarea, so specs
    can only ever use the fixed key vocabulary above - free-typed keys were
    the main way a spec would silently fail to show up in category facets
    (collect_facets groups purely by exact key string)."""

    template_name = "admin/catalog/widgets/specs_widget.html"

    class Media:
        js = ("admin/catalog/specs_widget.js",)
        css = {"all": ("admin/catalog/specs_widget.css",)}

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if isinstance(value, str):
            try:
                value = json.loads(value) if value else {}
            except (TypeError, ValueError):
                value = {}
        rows = list((value or {}).items())
        if not rows:
            rows = [("", "")]
        context["widget"]["rows"] = rows
        context["widget"]["key_choices"] = SPEC_KEY_CHOICES
        return context

    def value_from_datadict(self, data, files, name):
        keys = data.getlist(f"{name}_key")
        values = data.getlist(f"{name}_value")
        specs = {}
        for key, val in zip(keys, values):
            key = (key or "").strip()
            val = (val or "").strip()
            if key and val:
                specs[key] = _coerce_value(val)
        return specs

    def value_omitted_from_data(self, data, files, name):
        return False
