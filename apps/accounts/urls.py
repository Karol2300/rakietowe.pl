from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="core:home"), name="logout"),
    path("register/", views.register, name="register"),
    path("", views.dashboard, name="dashboard"),
    path("profile/", views.profile, name="profile"),
    path(
        "password/",
        auth_views.PasswordChangeView.as_view(
            template_name="accounts/password_change.html",
            success_url=reverse_lazy("accounts:password_change_done"),
        ),
        name="password_change",
    ),
    path(
        "password/done/",
        auth_views.PasswordChangeDoneView.as_view(template_name="accounts/password_change_done.html"),
        name="password_change_done",
    ),
    path("addresses/", views.address_list, name="address_list"),
    path("addresses/add/", views.address_form, name="address_add"),
    path("addresses/<int:address_id>/edit/", views.address_form, name="address_edit"),
    path("addresses/<int:address_id>/delete/", views.address_delete, name="address_delete"),
    path("loyalty/", views.loyalty, name="loyalty"),
    path("payment-methods/", views.payment_methods, name="payment_methods"),
]
