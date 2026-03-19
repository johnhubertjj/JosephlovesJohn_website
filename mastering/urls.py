from django.urls import path

from . import views

app_name = "mastering"

urlpatterns = [
    path("", views.home, name="home"),
    # Placeholder route for future mastering subfolders.
    path("<slug:subfolder>/", views.subfolder, name="subfolder"),
]
