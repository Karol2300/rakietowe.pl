"""
Django settings for the racket-shop project.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "django.contrib.postgres",
    # third-party
    "mptt",
    # local apps
    "apps.core",
    "apps.accounts",
    "apps.catalog",
    "apps.reviews",
    "apps.cart",
    "apps.orders",
    "apps.coupons",
    "apps.shipping",
    "apps.loyalty",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "apps.catalog.context_processors.sport_navigation",
                "apps.cart.context_processors.cart_summary",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases

DATABASES = {
    "default": env.db("DATABASE_URL"),
}


# Custom user model

AUTH_USER_MODEL = "accounts.User"


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = "en"

LANGUAGES = [
    ("en", "English"),
    ("pl", "Polski"),
]

LOCALE_PATHS = [BASE_DIR / "locale"]

TIME_ZONE = "Europe/Warsaw"

USE_I18N = True

USE_TZ = True


# Static & media files

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Email

EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@racket-shop.example")


# Store-wide constants

BASE_CURRENCY = "PLN"
SUPPORTED_CURRENCIES = ["PLN", "EUR", "USD"]
LOYALTY_POINTS_PER_PLN = env.float("LOYALTY_POINTS_PER_PLN", default=0.1)  # 1 point per 10 PLN spent

SITE_URL = env("SITE_URL", default="http://localhost:8000")

# PayU (primary payment provider) - REST API v2.1. Leave blank to use the
# local mock provider for development; see apps/orders/payments.py.
PAYU_POS_ID = env("PAYU_POS_ID", default="")
PAYU_CLIENT_ID = env("PAYU_CLIENT_ID", default="")
PAYU_CLIENT_SECRET = env("PAYU_CLIENT_SECRET", default="")
PAYU_SECOND_KEY = env("PAYU_SECOND_KEY", default="")
PAYU_SANDBOX = env.bool("PAYU_SANDBOX", default=True)

# Stripe (secondary payment provider, international customers)
STRIPE_PUBLISHABLE_KEY = env("STRIPE_PUBLISHABLE_KEY", default="")
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="")

# Seller details for VAT invoices - placeholder demo values, replace with the
# real registered business details before going live.
STORE_LEGAL_NAME = env("STORE_LEGAL_NAME", default="Racket Sports Shop Sp. z o.o.")
STORE_VAT_ID = env("STORE_VAT_ID", default="PL0000000000")
STORE_ADDRESS_LINE = env("STORE_ADDRESS_LINE", default="ul. Sportowa 1")
STORE_CITY_LINE = env("STORE_CITY_LINE", default="00-001 Warszawa, Poland")
