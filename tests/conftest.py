"""Shared pytest fixtures for the JosephlovesJohn test suite."""

from pathlib import Path

import pytest
from main_site import views as main_site_views


@pytest.fixture
def static_base_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point main site static-file helpers at a temporary project root.

    :param monkeypatch: Pytest monkeypatch fixture.
    :param tmp_path: Temporary directory unique to the test invocation.
    :returns: The temporary ``static`` directory path.
    """
    monkeypatch.setattr(main_site_views.settings, "BASE_DIR", tmp_path, raising=False)
    static_dir = tmp_path / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    return static_dir


@pytest.fixture
def create_static_asset(static_base_dir: Path):
    """Create a temporary static asset and return its relative path.

    :param static_base_dir: Temporary static directory fixture.
    :returns: A helper that creates files relative to ``static/``.
    """

    def _create(relative_path: str, content: bytes = b"asset") -> str:
        target = static_base_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return relative_path

    return _create
