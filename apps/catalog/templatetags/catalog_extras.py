from django import template

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
    """Turn a spec/attribute key like 'string_pattern' into 'string pattern'
    for display - CSS text-transform: capitalize handles the casing."""
    return str(key).replace("_", " ")


@register.simple_tag
def is_selected(selected_facets, key, value):
    values = selected_facets.get(key) or []
    return str(value) in [str(v) for v in values]


@register.simple_tag
def star_symbols(rating, max_stars=5):
    """Render a rounded whole-star string, e.g. '★★★★☆', for display-only use."""
    full = max(0, min(max_stars, round(float(rating or 0))))
    return "★" * full + "☆" * (max_stars - full)
