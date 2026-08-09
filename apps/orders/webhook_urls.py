from django.urls import path

from . import views

app_name = "order_webhooks"

urlpatterns = [
    path("payu/", views.payu_webhook, name="payu_webhook"),
    path("stripe/", views.stripe_webhook, name="stripe_webhook"),
]
