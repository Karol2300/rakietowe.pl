"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from apps.catalog.sitemaps import CategorySitemap, ProductSitemap
from apps.core.sitemaps import StaticViewSitemap
from apps.core.views import robots_txt, switch_language

sitemaps = {
    "products": ProductSitemap,
    "categories": CategorySitemap,
    "static": StaticViewSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/setlang/', switch_language, name='set_language'),
    path('webhooks/', include('apps.orders.webhook_urls')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    path('robots.txt', robots_txt, name='robots_txt'),
]

urlpatterns += i18n_patterns(
    path('', include('apps.core.urls')),
    path('', include('apps.catalog.urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('', include('apps.reviews.urls')),
    path('', include('apps.cart.urls')),
    path('checkout/', include('apps.orders.urls')),
    path('account/orders/', include('apps.orders.account_urls')),
    prefix_default_language=True,
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
