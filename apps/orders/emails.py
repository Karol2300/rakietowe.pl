from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


def _order_recipient(order):
    return order.guest_email or (order.user.email if order.user else None)


def _send(order_or_return, template, subject, context):
    order = getattr(order_or_return, "order", order_or_return)
    to_email = _order_recipient(order)
    if not to_email:
        return
    message = render_to_string(template, context)
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [to_email])


def send_order_confirmation_email(order):
    _send(
        order,
        "orders/email/order_confirmed.txt",
        f"Order {order.order_number} confirmed - Racket Sports Shop",
        {"order": order},
    )


def send_order_shipped_email(order):
    _send(
        order,
        "orders/email/order_shipped.txt",
        f"Order {order.order_number} has shipped - Racket Sports Shop",
        {"order": order},
    )


def send_order_delivered_email(order):
    _send(
        order,
        "orders/email/order_delivered.txt",
        f"Order {order.order_number} delivered - Racket Sports Shop",
        {"order": order},
    )


def send_order_cancelled_email(order, refunded=False):
    _send(
        order,
        "orders/email/order_cancelled.txt",
        f"Order {order.order_number} cancelled - Racket Sports Shop",
        {"order": order, "refunded": refunded},
    )


def send_return_status_email(return_request):
    _send(
        return_request,
        "orders/email/return_status.txt",
        f"Update on your return for order {return_request.order.order_number} - Racket Sports Shop",
        {"return_request": return_request, "order": return_request.order},
    )
