from django import forms
from django.utils.translation import gettext_lazy as _

from apps.shipping.models import ShippingMethod


class ShippingMethodChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, method):
        cost = f"{method.flat_rate_pln} zł" if method.flat_rate_pln else "—"
        eta = _("%(min)s-%(max)s days") % {"min": method.estimated_days_min, "max": method.estimated_days_max}
        free_note = (
            _(", free over %(threshold)s zł") % {"threshold": method.free_shipping_threshold_pln}
            if method.free_shipping_threshold_pln
            else ""
        )
        return f"{method.name} — {cost} ({eta}{free_note})"


class CheckoutForm(forms.Form):
    guest_email = forms.EmailField(required=False, label=_("Email"))
    shipping_full_name = forms.CharField(label=_("Full name"), max_length=255)
    shipping_street = forms.CharField(label=_("Street address"), max_length=255)
    shipping_city = forms.CharField(label=_("City"), max_length=100)
    shipping_postal_code = forms.CharField(label=_("Postal code"), max_length=20)
    shipping_country = forms.CharField(label=_("Country"), max_length=2, initial="PL")
    shipping_phone = forms.CharField(label=_("Phone"), max_length=30, required=False)
    shipping_method = ShippingMethodChoiceField(
        queryset=ShippingMethod.objects.filter(is_active=True),
        label=_("Shipping method"),
        empty_label=None,
        widget=forms.RadioSelect,
    )
    inpost_locker_point_id = forms.CharField(label=_("InPost locker point"), max_length=50, required=False)
    coupon_code = forms.CharField(label=_("Coupon code"), max_length=32, required=False)

    def __init__(self, *args, user_authenticated=False, **kwargs):
        super().__init__(*args, **kwargs)
        if user_authenticated:
            self.fields["guest_email"].widget = forms.HiddenInput()

    def clean(self):
        cleaned = super().clean()
        method = cleaned.get("shipping_method")
        if method and method.requires_locker_selection and not cleaned.get("inpost_locker_point_id"):
            self.add_error("inpost_locker_point_id", _("Please choose a parcel locker for InPost delivery."))
        return cleaned
