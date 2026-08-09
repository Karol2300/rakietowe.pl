from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


def send_order_confirmation_email(order):
    to_email = order.guest_email or (order.user.email if order.user else None)
    if not to_email:
        return
    subject = f"Order {order.order_number} confirmed - Racket Sports Shop"
    message = render_to_string("orders/email/order_confirmed.txt", {"order": order})
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [to_email])
