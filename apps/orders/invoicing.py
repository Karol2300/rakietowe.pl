from decimal import Decimal

from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone

from .models import Invoice

VAT_RATE = Decimal("0.23")  # Poland standard VAT rate


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


def generate_invoice(order):
    """Create the Invoice row and render its VAT invoice PDF. Called once,
    from within fulfill_paid_order's transaction, right after an order is
    marked paid."""
    if hasattr(order, "invoice"):
        return order.invoice

    net_total = (order.total / (1 + VAT_RATE)).quantize(Decimal("0.01"))
    vat_amount = order.total - net_total

    invoice = Invoice.objects.create(invoice_number=_next_invoice_number(), order=order)

    html = render_to_string("orders/invoice_pdf.html", {
        "order": order,
        "invoice": invoice,
        "vat_rate_percent": int(VAT_RATE * 100),
        "net_total": net_total,
        "vat_amount": vat_amount,
        "store_legal_name": settings.STORE_LEGAL_NAME,
        "store_vat_id": settings.STORE_VAT_ID,
        "store_address_line": settings.STORE_ADDRESS_LINE,
        "store_city_line": settings.STORE_CITY_LINE,
    })

    from weasyprint import HTML  # imported lazily so the app still starts if the native libs are ever unavailable

    pdf_bytes = HTML(string=html, base_url=settings.SITE_URL).write_pdf()
    invoice.pdf_file.save(f"{invoice.invoice_number.replace('/', '-')}.pdf", ContentFile(pdf_bytes), save=True)
    return invoice
