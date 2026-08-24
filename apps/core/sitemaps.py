from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5
    i18n = True
    alternates = True

    def items(self):
        return ["core:home", "core:privacy_policy", "core:terms"]

    def location(self, item):
        return reverse(item)
