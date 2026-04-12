"""Top-level URL configuration for the JosephlovesJohn project."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("shop/", include("shop.urls")),
    path("mastering-services/", include("mastering.urls")),
    path("", include("main_site.urls")),
]
