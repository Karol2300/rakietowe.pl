from .models import Cart, CartItem


def get_cart(request, create=True):
    if request.user.is_authenticated:
        if create:
            cart, _ = Cart.objects.get_or_create(user=request.user)
            return cart
        return Cart.objects.filter(user=request.user).first()

    if not request.session.session_key:
        if not create:
            return None
        request.session.create()
    session_key = request.session.session_key
    if not session_key:
        return None
    if create:
        cart, _ = Cart.objects.get_or_create(user=None, session_key=session_key)
        return cart
    return Cart.objects.filter(user=None, session_key=session_key).first()


def add_item(cart, variant, quantity=1):
    item, created = CartItem.objects.get_or_create(cart=cart, variant=variant, defaults={"quantity": quantity})
    if not created:
        item.quantity += quantity
    item.quantity = min(item.quantity, variant.stock_quantity)
    item.save()
    return item


def merge_session_cart_into_user_cart(request, user):
    session_key = request.session.session_key
    if not session_key:
        return
    session_cart = Cart.objects.filter(user=None, session_key=session_key).first()
    if not session_cart:
        return

    user_cart, _ = Cart.objects.get_or_create(user=user)
    for item in session_cart.items.select_related("variant"):
        existing = user_cart.items.filter(variant=item.variant).first()
        if existing:
            existing.quantity = min(existing.quantity + item.quantity, item.variant.stock_quantity)
            existing.save()
        else:
            item.cart = user_cart
            item.quantity = min(item.quantity, item.variant.stock_quantity)
            item.save()
    session_cart.delete()


def cart_item_count(cart):
    if not cart:
        return 0
    return sum(item.quantity for item in cart.items.all())


def cart_subtotal(cart):
    if not cart:
        return 0
    return sum(item.line_total for item in cart.items.all())
