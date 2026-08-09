from django.apps import AppConfig


class CartConfig(AppConfig):
    name = 'apps.cart'

    def ready(self):
        from . import signals  # noqa: F401
