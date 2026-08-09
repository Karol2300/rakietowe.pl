"""
Payment provider abstraction.

Each provider implements create_payment(order, request) -> redirect URL the
customer is sent to, and confirm_from_webhook(request) -> the Order that was
paid (or None). Real credentials are read from settings/env; when a provider
isn't configured, MockProvider is used instead so the checkout flow can be
developed and tested without a live PayU/Stripe account. See README notes in
.env.example for exactly which variables to set to go live.
"""

import hashlib
import hmac
import json

import requests
import stripe
from django.conf import settings
from django.urls import reverse

from apps.orders.models import Order


class PaymentError(Exception):
    pass


class BasePaymentProvider:
    name = None

    def create_payment(self, order, request):
        raise NotImplementedError

    def confirm_from_webhook(self, request):
        raise NotImplementedError

    def refund(self, order, amount):
        raise NotImplementedError


class PayUProvider(BasePaymentProvider):
    name = "payu"

    def __init__(self):
        self.base_url = "https://secure.snd.payu.com" if settings.PAYU_SANDBOX else "https://secure.payu.com"

    def _get_access_token(self):
        response = requests.post(
            f"{self.base_url}/pl/standard/user/oauth/authorize",
            data={
                "grant_type": "client_credentials",
                "client_id": settings.PAYU_CLIENT_ID,
                "client_secret": settings.PAYU_CLIENT_SECRET,
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.json()["access_token"]

    def create_payment(self, order, request):
        token = self._get_access_token()
        site_url = settings.SITE_URL.rstrip("/")
        payload = {
            "notifyUrl": f"{site_url}{reverse('order_webhooks:payu_webhook')}",
            "continueUrl": f"{site_url}{reverse('orders:payment_return', args=[order.order_number])}",
            "customerIp": request.META.get("REMOTE_ADDR", "127.0.0.1"),
            "merchantPosId": settings.PAYU_POS_ID,
            "description": f"Racket Sports Shop order {order.order_number}",
            "currencyCode": order.currency,
            "totalAmount": str(int(order.total * 100)),
            "extOrderId": order.order_number,
            "buyer": {"email": order.guest_email or order.user.email},
            "products": [
                {
                    "name": item.product_name,
                    "unitPrice": str(int(item.unit_price * 100)),
                    "quantity": str(item.quantity),
                }
                for item in order.items.all()
            ],
        }
        response = requests.post(
            f"{self.base_url}/api/v2_1/orders",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=10,
            allow_redirects=False,
        )
        if response.status_code not in (200, 201, 302):
            raise PaymentError(f"PayU order creation failed: {response.status_code} {response.text}")
        data = response.json()
        redirect_uri = data.get("redirectUri")
        order.payment_provider = Order.PaymentProvider.PAYU
        order.payment_reference = data.get("orderId", "")
        order.save(update_fields=["payment_provider", "payment_reference"])
        return redirect_uri

    def confirm_from_webhook(self, request):
        signature_header = request.headers.get("OpenPayU-Signature", "")
        signature = dict(part.split("=", 1) for part in signature_header.split(";") if "=" in part).get("signature")
        expected = hashlib.md5(request.body + settings.PAYU_SECOND_KEY.encode()).hexdigest()
        if not signature or signature != expected:
            raise PaymentError("Invalid PayU webhook signature")

        payload = json.loads(request.body)
        order_data = payload.get("order", {})
        order_number = order_data.get("extOrderId")
        status = order_data.get("status")
        order = Order.objects.filter(order_number=order_number).first()
        if not order:
            return None
        if status == "COMPLETED":
            return order
        return None

    def refund(self, order, amount):
        token = self._get_access_token()
        response = requests.post(
            f"{self.base_url}/api/v2_1/orders/{order.payment_reference}/refunds",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            data=json.dumps({"refund": {"description": f"Refund for {order.order_number}", "amount": str(int(amount * 100))}}),
            timeout=10,
        )
        if response.status_code not in (200, 201):
            raise PaymentError(f"PayU refund failed: {response.status_code} {response.text}")
        return True


class StripeProvider(BasePaymentProvider):
    name = "stripe"

    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def create_payment(self, order, request):
        site_url = settings.SITE_URL.rstrip("/")
        session = stripe.checkout.Session.create(
            mode="payment",
            client_reference_id=order.order_number,
            customer_email=order.guest_email or order.user.email,
            line_items=[
                {
                    "price_data": {
                        "currency": order.currency.lower(),
                        "product_data": {"name": item.product_name},
                        "unit_amount": int(item.unit_price * 100),
                    },
                    "quantity": item.quantity,
                }
                for item in order.items.all()
            ],
            shipping_options=[{
                "shipping_rate_data": {
                    "type": "fixed_amount",
                    "fixed_amount": {"amount": int(order.shipping_cost * 100), "currency": order.currency.lower()},
                    "display_name": order.shipping_method.name if order.shipping_method else "Shipping",
                }
            }],
            success_url=f"{site_url}{reverse('orders:payment_return', args=[order.order_number])}",
            cancel_url=f"{site_url}{reverse('orders:checkout')}",
            metadata={"order_number": order.order_number},
        )
        order.payment_provider = Order.PaymentProvider.STRIPE
        order.payment_reference = session.id
        order.save(update_fields=["payment_provider", "payment_reference"])
        return session.url

    def confirm_from_webhook(self, request):
        sig_header = request.headers.get("Stripe-Signature", "")
        try:
            event = stripe.Webhook.construct_event(request.body, sig_header, settings.STRIPE_WEBHOOK_SECRET)
        except (ValueError, stripe.error.SignatureVerificationError) as exc:
            raise PaymentError(str(exc)) from exc

        if event["type"] != "checkout.session.completed":
            return None
        order_number = event["data"]["object"].get("metadata", {}).get("order_number")
        return Order.objects.filter(order_number=order_number).first()

    def refund(self, order, amount):
        session = stripe.checkout.Session.retrieve(order.payment_reference)
        if not session.payment_intent:
            raise PaymentError("Stripe session has no completed payment to refund")
        stripe.Refund.create(payment_intent=session.payment_intent, amount=int(amount * 100))
        return True


class MockProvider(BasePaymentProvider):
    """Local development stand-in used when no real PayU/Stripe credentials
    are configured. Sends the customer to an on-site page that simulates the
    provider's redirect + webhook confirmation, so the full pending -> paid
    flow (stock decrement, loyalty points, confirmation email) stays real."""

    name = "mock"

    def create_payment(self, order, request):
        order.payment_provider = order.payment_provider or Order.PaymentProvider.PAYU
        order.save(update_fields=["payment_provider"])
        return reverse("orders:mock_payment", args=[order.order_number])

    def confirm_from_webhook(self, request):
        order_number = request.POST.get("order_number")
        return Order.objects.filter(order_number=order_number).first()

    def refund(self, order, amount):
        return True


def is_payu_configured():
    return bool(settings.PAYU_POS_ID and settings.PAYU_CLIENT_ID and settings.PAYU_CLIENT_SECRET)


def is_stripe_configured():
    return bool(settings.STRIPE_SECRET_KEY)


def get_provider(name):
    if name == "payu":
        return PayUProvider() if is_payu_configured() else MockProvider()
    if name == "stripe":
        return StripeProvider() if is_stripe_configured() else MockProvider()
    raise ValueError(f"Unknown payment provider: {name}")
