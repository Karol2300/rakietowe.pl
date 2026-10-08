from django.utils.translation import gettext_lazy as _

# Category.name is plain database content, so it is translated at render
# time by looking the stored name up in the catalog (catalog_extras.
# translate_name). makemessages can't see that lookup, and would mark any
# translation it can't find in the source as obsolete - declaring the names
# here keeps them extracted. Root names (Tennis, Squash, ...) already come
# from Sport.choices. When you add a category, add its name here too.
CATEGORY_NAME_TERMS = [
    _("Rackets"), _("Power Rackets"), _("Control Rackets"), _("Tweener Rackets"),
    _("Strings"), _("Balls"), _("Bags"), _("Shoes"), _("Apparel"),
    _("Eyewear"), _("Shuttlecocks"), _("Paddles"), _("Rubbers"), _("Tables"),
]
