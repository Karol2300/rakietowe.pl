from django.urls import path

from . import views

app_name = "order_account"

urlpatterns = [
    path("", views.order_history, name="list"),
    path("<str:order_number>/", views.order_detail, name="detail"),
]
