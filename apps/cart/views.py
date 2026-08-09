from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.catalog.models import Product, ProductVariant

from . import services
from .models import CartItem, Wishlist, WishlistItem


@require_POST
def add_to_cart(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    variant_id = request.POST.get("variant")
    if variant_id:
        variant = get_object_or_404(ProductVariant, id=variant_id, product=product, is_active=True)
    else:
        variant = product.variants.filter(is_active=True).first()

    if not variant or not variant.in_stock:
        messages.error(request, _("Sorry, that item is out of stock."))
        return redirect(reverse("catalog:product_detail", args=[slug]))

    try:
        quantity = max(1, int(request.POST.get("quantity", 1)))
    except ValueError:
        quantity = 1

    cart = services.get_cart(request)
    services.add_item(cart, variant, quantity)
    messages.success(request, _("Added %(name)s to your cart.") % {"name": product.name})
    return redirect(reverse("cart:cart_detail"))


def cart_detail(request):
    cart = services.get_cart(request, create=False)
    items = cart.items.select_related("variant__product", "variant__product__brand").all() if cart else []
    context = {
        "cart": cart,
        "items": items,
        "subtotal": services.cart_subtotal(cart),
    }
    return render(request, "cart/cart_detail.html", context)


@require_POST
def update_cart_item(request, item_id):
    cart = services.get_cart(request, create=False)
    item = get_object_or_404(CartItem, id=item_id, cart=cart)
    try:
        quantity = int(request.POST.get("quantity", 1))
    except ValueError:
        quantity = item.quantity

    if quantity <= 0:
        item.delete()
    else:
        item.quantity = min(quantity, item.variant.stock_quantity)
        item.save()
    return redirect(reverse("cart:cart_detail"))


@require_POST
def remove_cart_item(request, item_id):
    cart = services.get_cart(request, create=False)
    item = get_object_or_404(CartItem, id=item_id, cart=cart)
    item.delete()
    return redirect(reverse("cart:cart_detail"))


@login_required
@require_POST
def toggle_wishlist(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    item, created = WishlistItem.objects.get_or_create(wishlist=wishlist, product=product)
    if not created:
        item.delete()
        messages.success(request, _("Removed %(name)s from your wishlist.") % {"name": product.name})
    else:
        messages.success(request, _("Added %(name)s to your wishlist.") % {"name": product.name})
    return redirect(reverse("catalog:product_detail", args=[slug]))
