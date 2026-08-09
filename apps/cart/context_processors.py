from . import services


def cart_summary(request):
    cart = services.get_cart(request, create=False)
    return {"cart_item_count": services.cart_item_count(cart)}
