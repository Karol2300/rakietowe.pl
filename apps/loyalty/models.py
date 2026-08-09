from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class LoyaltyAccount(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="loyalty_account"
    )
    points_balance = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user}: {self.points_balance} pts"


class LoyaltyTransaction(models.Model):
    class Kind(models.TextChoices):
        EARNED = "earned", _("Earned")
        REDEEMED = "redeemed", _("Redeemed")

    account = models.ForeignKey(LoyaltyAccount, on_delete=models.CASCADE, related_name="transactions")
    order = models.ForeignKey(
        "orders.Order", on_delete=models.SET_NULL, null=True, blank=True, related_name="loyalty_transactions"
    )
    kind = models.CharField(max_length=10, choices=Kind.choices)
    points = models.IntegerField(help_text="Positive for earned, negative for redeemed")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.account.user}: {self.kind} {self.points}pts"
