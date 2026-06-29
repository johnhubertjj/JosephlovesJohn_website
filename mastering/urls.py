"""URL patterns for the mastering services site."""

from django.urls import path

from . import views

app_name = "mastering"

urlpatterns = [
    path("", views.home, name="home"),
    path("intake/", views.intake, name="intake"),
    # Placeholder route for future mastering subfolders.
    path("<slug:subfolder>/", views.subfolder, name="subfolder"),
]
