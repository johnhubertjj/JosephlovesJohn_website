"""Tests for environment-driven Django settings helpers."""

import importlib
from pathlib import Path

import pytest
from josephlovesjohn_site import settings

pytestmark = pytest.mark.smoke


def test_env_bool_parses_truthy_and_falsy_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """Boolean helper should understand common truthy and falsy env values."""
    monkeypatch.setenv("TEST_BOOL", "yes")
    assert settings._env_bool("TEST_BOOL") is True

    monkeypatch.setenv("TEST_BOOL", "0")
    assert settings._env_bool("TEST_BOOL", default=True) is False


def test_env_int_falls_back_for_invalid_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """Integer helper should fall back safely for invalid env values."""
    monkeypatch.setenv("TEST_INT", "42")
    assert settings._env_int("TEST_INT", default=1) == 42

    monkeypatch.setenv("TEST_INT", "invalid")
    assert settings._env_int("TEST_INT", default=7) == 7


def test_env_list_strips_blank_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    """List helper should return normalized comma-separated values."""
    monkeypatch.setenv("TEST_LIST", "example.com, www.example.com, ,api.example.com")

    assert settings._env_list("TEST_LIST") == [
        "example.com",
        "www.example.com",
        "api.example.com",
    ]


def test_settings_use_sqlite_when_database_url_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """The project should keep SQLite as the local-development fallback."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DOTENV_PATH", str(Path(__file__).parent / "missing.env"))

    reloaded = importlib.reload(settings)
    try:
        assert reloaded.DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3"
        assert str(reloaded.DATABASES["default"]["NAME"]).endswith("db.sqlite3")
    finally:
        monkeypatch.delenv("DOTENV_PATH", raising=False)
        importlib.reload(settings)


def test_settings_use_database_url_when_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """Production-style DATABASE_URL values should configure Postgres."""
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://render_user:secret@render-postgres:5432/jlj_prod",
    )
    monkeypatch.setenv("DATABASE_CONN_MAX_AGE", "900")
    monkeypatch.setenv("DOTENV_PATH", str(Path(__file__).parent / "missing.env"))

    reloaded = importlib.reload(settings)
    try:
        assert reloaded.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"
        assert reloaded.DATABASES["default"]["NAME"] == "jlj_prod"
        assert reloaded.DATABASES["default"]["USER"] == "render_user"
        assert reloaded.DATABASES["default"]["HOST"] == "render-postgres"
        assert reloaded.DATABASES["default"]["PORT"] == 5432
        assert reloaded.DATABASES["default"]["CONN_MAX_AGE"] == 900
    finally:
        monkeypatch.delenv("DOTENV_PATH", raising=False)
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("DATABASE_CONN_MAX_AGE", raising=False)
        importlib.reload(settings)


def test_settings_load_dotenv_values_when_present(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Local .env values should be loaded when the shell does not provide them."""
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "DEBUG=false\nSECRET_KEY=from-dotenv\nALLOWED_HOSTS=example.com,www.example.com\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("DOTENV_PATH", str(dotenv_path))
    monkeypatch.delenv("DEBUG", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("ALLOWED_HOSTS", raising=False)

    reloaded = importlib.reload(settings)
    try:
        assert reloaded.DEBUG is False
        assert reloaded.SECRET_KEY == "from-dotenv"
        assert reloaded.ALLOWED_HOSTS == ["example.com", "www.example.com"]
    finally:
        monkeypatch.delenv("DOTENV_PATH", raising=False)
        monkeypatch.delenv("DEBUG", raising=False)
        monkeypatch.delenv("SECRET_KEY", raising=False)
        monkeypatch.delenv("ALLOWED_HOSTS", raising=False)
        importlib.reload(settings)


def test_dotenv_does_not_override_real_environment_variables(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Actual environment variables should take precedence over .env values."""
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("SECRET_KEY=from-dotenv\n", encoding="utf-8")

    monkeypatch.setenv("DOTENV_PATH", str(dotenv_path))
    monkeypatch.setenv("SECRET_KEY", "from-shell")

    reloaded = importlib.reload(settings)
    try:
        assert reloaded.SECRET_KEY == "from-shell"
    finally:
        monkeypatch.delenv("DOTENV_PATH", raising=False)
        monkeypatch.delenv("SECRET_KEY", raising=False)
        importlib.reload(settings)


def test_settings_expose_plausible_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    """Analytics settings should read Plausible values from the environment."""
    monkeypatch.setenv("PLAUSIBLE_DOMAIN", "josephlovesjohn.com")
    monkeypatch.setenv("PLAUSIBLE_SCRIPT_SRC", "https://plausible.example/js/pa-example.js")
    monkeypatch.setenv("DOTENV_PATH", str(Path(__file__).parent / "missing.env"))

    reloaded = importlib.reload(settings)
    try:
        assert reloaded.PLAUSIBLE_DOMAIN == "josephlovesjohn.com"
        assert reloaded.PLAUSIBLE_SCRIPT_SRC == "https://plausible.example/js/pa-example.js"
    finally:
        monkeypatch.delenv("PLAUSIBLE_DOMAIN", raising=False)
        monkeypatch.delenv("PLAUSIBLE_SCRIPT_SRC", raising=False)
        monkeypatch.delenv("DOTENV_PATH", raising=False)
        importlib.reload(settings)
