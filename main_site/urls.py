"""URL patterns for the main site pages."""

from django.urls import path

from . import views

app_name = "main_site"

urlpatterns = [
    path("", views.main, name="main"),
    path("intro/", views.intro, name="intro"),
    path("music/", views.music, name="music"),
    path("music/<slug:slug>/", views.music_track, name="music_track"),
    path("art/", views.art, name="art"),
    path("contact/", views.contact, name="contact"),
    path("privacy/", views.privacy, name="privacy"),
    path("cookies/", views.cookies, name="cookies"),
    path("terms/", views.terms, name="terms"),
    path("refunds/", views.refunds, name="refunds"),
]
