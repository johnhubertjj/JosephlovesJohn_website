"""URL patterns for the main site pages."""

from django.urls import path

from . import views

app_name = "main_site"

urlpatterns = [
    path("", views.main, name="main"),
    path("intro/", views.intro, name="intro"),
    path("music/", views.music, name="music"),
    path("art/", views.art, name="art"),
    path("contact/", views.contact, name="contact"),
]
