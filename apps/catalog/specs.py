from django.utils.translation import gettext_lazy as _

# Human-readable (and translatable) names for the keys stored in
# Product.specs and ProductVariant.attributes. Storage keeps the raw
# snake_case keys - filter URLs and form field names depend on them - and
# only display goes through these labels. Unknown keys fall back to the
# key with underscores replaced (see catalog_extras.spec_label).
SPEC_LABELS = {
    "weight_g": _("Weight (g)"),
    "balance_point_mm": _("Balance point (mm)"),
    "stiffness_ra": _("Stiffness (RA)"),
    "head_size_sq_in": _("Head size (sq in)"),
    "string_pattern": _("String pattern"),
    "flex": _("Flex"),
    "balance": _("Balance"),
    "blade_material": _("Blade material"),
    "speed_rating": _("Speed rating"),
    "spin_rating": _("Spin rating"),
    "control_rating": _("Control rating"),
    "handle_type": _("Handle type"),
    "sponge_thickness_mm": _("Sponge thickness (mm)"),
    "speed": _("Speed"),
    "spin": _("Spin"),
    "control": _("Control"),
    "gauge_mm": _("Gauge (mm)"),
    "material": _("Material"),
    "recommended_tension_lbs": _("Recommended tension (lbs)"),
    "pack_size": _("Pack size"),
    "capacity_l": _("Capacity (L)"),
    "compartments": _("Compartments"),
    "upper_material": _("Upper material"),
    "sole_type": _("Sole type"),
    "fit": _("Fit"),
    "lens_type": _("Lens type"),
    "uv_protection": _("UV protection"),
    "thickness_mm": _("Thickness (mm)"),
    "foldable": _("Foldable"),
    "indoor_outdoor": _("Indoor/outdoor"),
    # variant attribute keys
    "grip_size": _("Grip size"),
    "weight_class": _("Weight class"),
    "color": _("Color"),
    "shoe_size": _("Shoe size"),
    "apparel_size": _("Size"),
}

# The text values used across the catalog (see seed_products.specs_for).
# This list exists so makemessages can find them - spec_value() looks
# values up in the catalog at render time, which it can't extract from.
# Sizes (S/M/L, L1-L5, 3U-6U) and numbers are the same in every language.
SPEC_VALUE_TERMS = [
    _("Polyester"), _("Natural gut"), _("Synthetic gut"), _("Multifilament"),
    _("Nylon"), _("Nylon ripstop"), _("Thermal-lined polyester"),
    _("Cotton blend"), _("Recycled polyester"), _("Rubber/felt composite"),
    _("ABS plastic"), _("Goose feather"), _("Mesh"), _("Synthetic leather"),
    _("Knit"), _("Herringbone"), _("Gum rubber"), _("Multi-court"),
    _("Regular"), _("Slim"), _("Athletic"), _("Clear"), _("Anti-fog"),
    _("Polarized"), _("Indoor"), _("Outdoor"), _("Flexible"), _("Medium"),
    _("Stiff"), _("Head Heavy"), _("Even Balance"), _("Head Light"),
    _("All-wood"), _("Carbon composite"), _("Ayous/Carbon"), _("Max"),
    _("Flared (FL)"), _("Straight (ST)"), _("Concave (CS)"),
    _("Black"), _("Red"), _("Navy"), _("Grey"), _("Natural"), _("Yellow"),
    _("Blue"),
]
