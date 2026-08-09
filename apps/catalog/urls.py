from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("search/", views.search, name="search"),
    path("search/suggestions/", views.search_suggestions, name="search_suggestions"),
    path("c/<slug:slug>/", views.category_detail, name="category_detail"),
]
