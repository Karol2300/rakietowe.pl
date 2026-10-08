from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("search/", views.search, name="search"),
    path("search/suggestions/", views.search_suggestions, name="search_suggestions"),
    path("c/<slug:slug>/", views.category_detail, name="category_detail"),
    path("p/<slug:slug>/", views.product_detail, name="product_detail"),
    path("variant/<int:variant_id>/notify/", views.request_stock_notification, name="request_stock_notification"),
    path("p/<slug:slug>/toggle-compare/", views.toggle_compare, name="toggle_compare"),
    path("compare/", views.compare_view, name="compare"),
    path("compare/clear/", views.clear_compare, name="clear_compare"),
]
