from collections import defaultdict
from decimal import Decimal

from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone

from apps.catalog.models import VatRate

from .models import Invoice

# Shipping/delivery is taxed at the standard rate regardless of what VAT
# rate(s) the goods in the order carry.
SHIPPING_VAT_RATE = VatRate.STANDARD

TWO_PLACES = Decimal("0.01")


def _next_invoice_number():
    """Sequential per-year invoice numbering, e.g. FV/2026/000001.
    Must be called inside a transaction with Invoice rows locked by the
    caller to avoid duplicate numbers under concurrent payment confirmations.
    """
    year = timezone.now().year
    prefix = f"FV/{year}/"
    last = Invoice.objects.filter(invoice_number__startswith=prefix).order_by("-invoice_number").first()
    seq = int(last.invoice_number.rsplit("/", 1)[-1]) + 1 if last else 1
    return f"{prefix}{seq:06d}"


def _compute_vat_breakdown(order):
    """Group order items by VAT rate (each OrderItem carries a snapshot of
    its product's rate), allocate the order's discount proportionally
    across those groups by gross value, add shipping at the standard rate,
    then return one net/vat/gross row per rate plus the grand totals.

    Polish VAT invoices must show a net/VAT/gross breakdown per rate
    whenever an order mixes more than one - a single order.total figure
    with a single flat rate isn't sufficient once 8% items exist alongside
    23% ones.
    """
    gross_by_rate = defaultdict(Decimal)
    for item in order.items.all():
        gross_by_rate[item.vat_rate] += item.line_total

    subtotal = sum(gross_by_rate.values()) if gross_by_rate else Decimal("0")
    discount = order.discount_amount or Decimal("0")

    if subtotal > 0 and discount > 0:
        for rate in list(gross_by_rate):
            share = (gross_by_rate[rate] / subtotal) * discount
            gross_by_rate[rate] -= share.quantize(TWO_PLACES)

    if order.shipping_cost:
        gross_by_rate[SHIPPING_VAT_RATE] += order.shipping_cost

    rows = []
    net_total = Decimal("0")
    vat_total = Decimal("0")
    for rate in sorted(gross_by_rate, reverse=True):
        gross = gross_by_rate[rate]
        if gross <= 0:
            continue
        net = (gross / (1 + Decimal(rate) / 100)).quantize(TWO_PLACES)
        vat = gross - net
        rows.append({"rate": rate, "net": net, "vat": vat, "gross": gross})
        net_total += net
        vat_total += vat

    return rows, net_total, vat_total


def generate_invoice(order):
    """Create the Invoice row and render its VAT invoice PDF. Called once,
    from within fulfill_paid_order's transaction, right after an order is
    marked paid."""
    if hasattr(order, "invoice"):
        return order.invoice

    vat_rows, net_total, vat_total = _compute_vat_breakdown(order)

    invoice = Invoice.objects.create(invoice_number=_next_invoice_number(), order=order)

    html = render_to_string("orders/invoice_pdf.html", {
        "order": order,
        "invoice": invoice,
        "vat_rows": vat_rows,
        "net_total": net_total,
        "vat_amount": vat_total,
        "store_legal_name": settings.STORE_LEGAL_NAME,
        "store_vat_id": settings.STORE_VAT_ID,
        "store_address_line": settings.STORE_ADDRESS_LINE,
        "store_city_line": settings.STORE_CITY_LINE,
    })

    from weasyprint import HTML  # imported lazily so the app still starts if the native libs are ever unavailable

    pdf_bytes = HTML(string=html, base_url=settings.SITE_URL).write_pdf()
    invoice.pdf_file.save(f"{invoice.invoice_number.replace('/', '-')}.pdf", ContentFile(pdf_bytes), save=True)
    return invoice
