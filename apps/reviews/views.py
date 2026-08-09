from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.catalog.models import Product
from apps.orders.models import Order, OrderItem

from .forms import ReviewForm
from .models import Review


def _recalculate_rating(product):
    reviews = list(product.reviews.filter(is_visible=True))
    product.review_count = len(reviews)
    product.average_rating = round(sum(r.rating for r in reviews) / len(reviews), 2) if reviews else 0
    product.save(update_fields=["review_count", "average_rating"])


@login_required
@require_POST
def add_review(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    instance = Review.objects.filter(product=product, user=request.user).first()
    form = ReviewForm(request.POST, instance=instance)

    if form.is_valid():
        review = form.save(commit=False)
        review.product = product
        review.user = request.user
        review.verified_purchase = OrderItem.objects.filter(
            order__user=request.user,
            order__payment_status=Order.PaymentStatus.PAID,
            variant__product=product,
        ).exists()
        review.save()
        _recalculate_rating(product)
        messages.success(request, _("Thanks - your review has been posted."))
    else:
        messages.error(request, _("Please choose a rating and try again."))

    return redirect(reverse("catalog:product_detail", args=[slug]) + "#reviews")
