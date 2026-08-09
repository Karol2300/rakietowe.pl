from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("", views.checkout, name="checkout"),
    path("<str:order_number>/pay/", views.payment_select, name="payment_select"),
    path("<str:order_number>/pay/<str:provider>/", views.payment_start, name="payment_start"),
    path("<str:order_number>/return/", views.payment_return, name="payment_return"),
    path("<str:order_number>/mock/", views.mock_payment, name="mock_payment"),
    path("<str:order_number>/mock/confirm/", views.mock_confirm, name="mock_confirm"),
    path("<str:order_number>/mock/cancel/", views.mock_cancel, name="mock_cancel"),
    path("<str:order_number>/request-return/", views.request_return, name="request_return"),
    path("<str:order_number>/invoice/", views.download_invoice, name="download_invoice"),
]
