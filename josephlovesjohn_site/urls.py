"""Top-level URL configuration for the JosephlovesJohn project."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import URLPattern, URLResolver, include, path
from main_site.sitemaps import StaticViewSitemap
from main_site.views import robots_txt

sitemaps = {
    "pages": StaticViewSitemap(),
}

urlpatterns: list[URLPattern | URLResolver] = [
    path("admin/", admin.site.urls),
    path("robots.txt", robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("shop/", include("shop.urls")),
    path("mastering-services/", include("mastering.urls")),
    path("", include("main_site.urls")),
]

if settings.DEBUG:
    urlpatterns.extend(static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT))
