from django import template
from django.utils.translation import gettext as _

from apps.catalog.specs import SPEC_LABELS

register = template.Library()


@register.simple_tag(takes_context=True)
def query_transform(context, **kwargs):
    """Return the current request's querystring with the given params updated
    (or removed, if the value is None), preserving everything else - used to
    build pagination links that keep the active filters."""
    request = context["request"]
    updated = request.GET.copy()
    for key, value in kwargs.items():
        if value is None:
            updated.pop(key, None)
        else:
            updated[key] = value
    return updated.urlencode()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def spec_label(key):
    """Display name for a spec/variant key: the translated label from
    SPEC_LABELS, or - for a key nobody has labelled yet - the key itself
    with underscores turned into spaces."""
    label = SPEC_LABELS.get(str(key))
    return str(label) if label is not None else str(key).replace("_", " ")


@register.filter
def spec_value(value):
    """Display text for a spec/variant value. Booleans (and the 'true' /
    'false' text the facet checkboxes use) become Yes/No; other text is
    looked up in the translation catalog and falls back to itself, so
    numbers, sizes and anything untranslated pass through unchanged."""
    if value is True or value == "true":
        return _("Yes")
    if value is False or value == "false":
        return _("No")
    return _(str(value))


@register.filter
def translate_name(name):
    """Category.name is plain DB content, not a marked-up template string,
    so {% trans %} can't touch it and switching language never re-renders
    it. Root categories are named directly after Sport.choices labels
    (see seed_products.create_categories), which already have real PL
    translations - this runs the stored name through the same gettext
    catalog those labels use, so it picks up a translation when one
    exists and falls back to the original (English) name otherwise."""
    return _(name)


@register.simple_tag
def is_selected(selected_facets, key, value):
    values = selected_facets.get(key) or []
    return str(value) in [str(v) for v in values]


@register.simple_tag
def star_symbols(rating, max_stars=5):
    """Render a rounded whole-star string, e.g. '★★★★☆', for display-only use."""
    full = max(0, min(max_stars, round(float(rating or 0))))
    return "★" * full + "☆" * (max_stars - full)
