"""Application configuration tests."""

import pytest
from main_site.apps import MainSiteConfig
from mastering.apps import MasteringConfig
from shop.apps import ShopConfig

pytestmark = pytest.mark.smoke


def test_main_site_config_metadata() -> None:
    """The main site app config should expose the expected metadata."""
    assert MainSiteConfig.name == "main_site"
    assert MainSiteConfig.default_auto_field == "django.db.models.BigAutoField"


def test_mastering_config_metadata() -> None:
    """The mastering app config should expose the expected metadata."""
    assert MasteringConfig.name == "mastering"
    assert MasteringConfig.default_auto_field == "django.db.models.BigAutoField"


def test_shop_config_metadata() -> None:
    """The shop app config should expose the expected metadata."""
    assert ShopConfig.name == "shop"
    assert ShopConfig.default_auto_field == "django.db.models.BigAutoField"
