from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/item/<int:item_id>/update/", views.update_cart_item, name="update_item"),
    path("cart/item/<int:item_id>/remove/", views.remove_cart_item, name="remove_item"),
    path("p/<slug:slug>/add-to-cart/", views.add_to_cart, name="add_to_cart"),
    path("p/<slug:slug>/toggle-wishlist/", views.toggle_wishlist, name="toggle_wishlist"),
    path("wishlist/", views.wishlist_detail, name="wishlist"),
]
