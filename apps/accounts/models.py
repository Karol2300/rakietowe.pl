from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    email = models.EmailField(_("email address"), unique=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    payu_customer_ref = models.CharField(max_length=255, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    label = models.CharField(max_length=100, blank=True)
    full_name = models.CharField(max_length=255)
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=2, default="PL")
    phone = models.CharField(max_length=30, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "addresses"
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return f"{self.label or self.full_name} ({self.city})"
