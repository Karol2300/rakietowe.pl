import uuid

from django import forms
from django.contrib.auth import password_validation
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from .models import User


class RegistrationForm(forms.ModelForm):
    password1 = forms.CharField(label=_("Password"), widget=forms.PasswordInput, strip=False)
    password2 = forms.CharField(label=_("Confirm password"), widget=forms.PasswordInput, strip=False)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("An account with this email already exists."))
        return email

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(_("Passwords do not match."))
        password_validation.validate_password(password2)
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = f"{slugify(user.email.split('@')[0])}-{uuid.uuid4().hex[:8]}"
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user
