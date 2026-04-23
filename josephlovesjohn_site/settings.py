"""Django settings for the JosephlovesJohn project.

This module contains the environment-agnostic defaults used for local
development of the site and its supporting apps.
"""

import os
from pathlib import Path

import dj_database_url

from josephlovesjohn_site.sentry import setup_sentry_from_env


def _env_bool(name: str, default: bool = False) -> bool:
    """Parse a flexible boolean environment variable."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int = 0) -> int:
    """Parse an integer environment variable with a fallback."""
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value.strip())
    except ValueError:
        return default


def _env_list(name: str, default: list[str] | None = None) -> list[str]:
    """Parse a comma-separated list environment variable."""
    value = os.environ.get(name)
    if value is None:
        return list(default or [])
    return [item.strip() for item in value.split(",") if item.strip()]


def _load_dotenv(dotenv_path: Path) -> None:
    """Load simple KEY=VALUE pairs from a local .env file."""
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key or key in os.environ:
            continue

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]

        os.environ[key] = value


BASE_DIR = Path(__file__).resolve().parent.parent
DOTENV_PATH = Path(os.environ.get("DOTENV_PATH", BASE_DIR / ".env"))
_load_dotenv(DOTENV_PATH)

DEBUG = _env_bool("DEBUG", default=True)
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-change-me")
ALLOWED_HOSTS = _env_list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"] if DEBUG else [])
CSRF_TRUSTED_ORIGINS = _env_list("CSRF_TRUSTED_ORIGINS")
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "").strip().rstrip("/")

if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

if RENDER_EXTERNAL_URL and RENDER_EXTERNAL_URL not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(RENDER_EXTERNAL_URL)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sitemaps",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "main_site",
    "mastering",
    "shop",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "main_site.cache.SharedContentCacheContextMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "josephlovesjohn_site.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "main_site.context_processors.analytics",
                "shop.context_processors.cart_summary",
            ],
        },
    }
]

WSGI_APPLICATION = "josephlovesjohn_site.wsgi.application"
ASGI_APPLICATION = "josephlovesjohn_site.asgi.application"

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
DATABASE_CONN_MAX_AGE = _env_int("DATABASE_CONN_MAX_AGE", default=600 if not DEBUG else 0)
REDIS_URL = os.environ.get("REDIS_URL", "").strip()

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=DATABASE_CONN_MAX_AGE,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(BASE_DIR / "db.sqlite3"),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/London"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = os.environ.get("MEDIA_URL", "/media/").strip() or "/media/"
MEDIA_ROOT = BASE_DIR / "media"
SITE_URL = os.environ.get("SITE_URL", "").strip().rstrip("/")
if not SITE_URL and RENDER_EXTERNAL_URL:
    SITE_URL = RENDER_EXTERNAL_URL
if not SITE_URL and DEBUG:
    SITE_URL = "http://127.0.0.1:8000"
PUBLIC_ASSET_BASE_URL = os.environ.get("PUBLIC_ASSET_BASE_URL", "").strip().rstrip("/")
MEDIA_FILES_BUCKET_NAME = os.environ.get("MEDIA_FILES_BUCKET_NAME", "").strip()
MEDIA_FILES_ENDPOINT_URL = os.environ.get("MEDIA_FILES_ENDPOINT_URL", "").strip()
MEDIA_FILES_ACCESS_KEY_ID = os.environ.get("MEDIA_FILES_ACCESS_KEY_ID", "").strip()
MEDIA_FILES_SECRET_ACCESS_KEY = os.environ.get("MEDIA_FILES_SECRET_ACCESS_KEY", "").strip()
MEDIA_FILES_REGION = os.environ.get("MEDIA_FILES_REGION", "auto").strip() or "auto"
MEDIA_FILES_BASE_URL = os.environ.get("MEDIA_FILES_BASE_URL", "").strip().rstrip("/")
MEDIA_FILES_KEY_PREFIX = os.environ.get("MEDIA_FILES_KEY_PREFIX", "").strip().strip("/")
if MEDIA_FILES_BASE_URL and MEDIA_URL == "/media/":
    MEDIA_URL = f"{MEDIA_FILES_BASE_URL}/"
PRIVATE_DOWNLOADS_ROOT = Path(
    os.environ.get("PRIVATE_DOWNLOADS_ROOT", "").strip() or str(MEDIA_ROOT / "private_downloads")
)
PRIVATE_DOWNLOADS_BUCKET_NAME = os.environ.get("PRIVATE_DOWNLOADS_BUCKET_NAME", "").strip()
PRIVATE_DOWNLOADS_ENDPOINT_URL = os.environ.get("PRIVATE_DOWNLOADS_ENDPOINT_URL", "").strip()
PRIVATE_DOWNLOADS_ACCESS_KEY_ID = os.environ.get("PRIVATE_DOWNLOADS_ACCESS_KEY_ID", "").strip()
PRIVATE_DOWNLOADS_SECRET_ACCESS_KEY = os.environ.get("PRIVATE_DOWNLOADS_SECRET_ACCESS_KEY", "").strip()
PRIVATE_DOWNLOADS_REGION = os.environ.get("PRIVATE_DOWNLOADS_REGION", "auto").strip() or "auto"
PRIVATE_DOWNLOADS_KEY_PREFIX = os.environ.get("PRIVATE_DOWNLOADS_KEY_PREFIX", "").strip().strip("/")
PRIVATE_DOWNLOADS_URL_EXPIRY = _env_int("PRIVATE_DOWNLOADS_URL_EXPIRY", default=300)
PRIVATE_PREVIEWS_BUCKET_NAME = os.environ.get("PRIVATE_PREVIEWS_BUCKET_NAME", PRIVATE_DOWNLOADS_BUCKET_NAME).strip()
PRIVATE_PREVIEWS_ENDPOINT_URL = os.environ.get("PRIVATE_PREVIEWS_ENDPOINT_URL", PRIVATE_DOWNLOADS_ENDPOINT_URL).strip()
PRIVATE_PREVIEWS_ACCESS_KEY_ID = os.environ.get(
    "PRIVATE_PREVIEWS_ACCESS_KEY_ID",
    PRIVATE_DOWNLOADS_ACCESS_KEY_ID,
).strip()
PRIVATE_PREVIEWS_SECRET_ACCESS_KEY = os.environ.get(
    "PRIVATE_PREVIEWS_SECRET_ACCESS_KEY",
    PRIVATE_DOWNLOADS_SECRET_ACCESS_KEY,
).strip()
PRIVATE_PREVIEWS_REGION = os.environ.get("PRIVATE_PREVIEWS_REGION", PRIVATE_DOWNLOADS_REGION).strip() or "auto"
PRIVATE_PREVIEWS_KEY_PREFIX = os.environ.get("PRIVATE_PREVIEWS_KEY_PREFIX", PRIVATE_DOWNLOADS_KEY_PREFIX).strip().strip(
    "/"
)
PRIVATE_PREVIEWS_URL_EXPIRY = _env_int("PRIVATE_PREVIEWS_URL_EXPIRY", default=900)
SITE_CONTENT_CACHE_TTL = _env_int("SITE_CONTENT_CACHE_TTL", default=0 if DEBUG else 300)
CART_SUMMARY_CACHE_TTL = _env_int("CART_SUMMARY_CACHE_TTL", default=0 if DEBUG else 60)

STATICFILES_STORAGE_BACKEND = (
    "django.contrib.staticfiles.storage.StaticFilesStorage"
    if DEBUG
    else "whitenoise.storage.CompressedManifestStaticFilesStorage"
)
MEDIA_STORAGE_BACKEND = (
    "josephlovesjohn_site.storage.S3CompatibleMediaStorage"
    if MEDIA_FILES_BUCKET_NAME
    else "django.core.files.storage.FileSystemStorage"
)

STORAGES = {
    "default": {
        "BACKEND": MEDIA_STORAGE_BACKEND,
    },
    "staticfiles": {
        "BACKEND": STATICFILES_STORAGE_BACKEND,
    },
}

CACHES = (
    {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }
    if REDIS_URL
    else {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "josephlovesjohn-local-cache",
        }
    }
)

SESSION_ENGINE = (
    "django.contrib.sessions.backends.cached_db"
    if REDIS_URL
    else "django.contrib.sessions.backends.db"
)
SESSION_CACHE_ALIAS = "default"

WHITENOISE_AUTOREFRESH = DEBUG
WHITENOISE_USE_FINDERS = DEBUG
WHITENOISE_MAX_AGE = 60 if DEBUG else 31536000
VERIFY_STATIC_ASSET_FILES = _env_bool("VERIFY_STATIC_ASSET_FILES", default=DEBUG)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SECURE_SSL_REDIRECT = _env_bool("SECURE_SSL_REDIRECT", default=not DEBUG)
SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", default=not DEBUG)
CSRF_COOKIE_SECURE = _env_bool("CSRF_COOKIE_SECURE", default=not DEBUG)
SECURE_HSTS_SECONDS = _env_int("SECURE_HSTS_SECONDS", default=31536000 if not DEBUG else 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=not DEBUG)
SECURE_HSTS_PRELOAD = _env_bool("SECURE_HSTS_PRELOAD", default=False)
SECURE_CONTENT_TYPE_NOSNIFF = _env_bool("SECURE_CONTENT_TYPE_NOSNIFF", default=True)
SECURE_REFERRER_POLICY = os.environ.get("SECURE_REFERRER_POLICY", "strict-origin-when-cross-origin")

if _env_bool("USE_X_FORWARDED_PROTO", default=False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_API_VERSION = os.environ.get("STRIPE_API_VERSION", "2026-02-25.clover")
STRIPE_CURRENCY = os.environ.get("STRIPE_CURRENCY", "gbp")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
PLAUSIBLE_DOMAIN = os.environ.get("PLAUSIBLE_DOMAIN", "").strip()
PLAUSIBLE_SCRIPT_SRC = os.environ.get(
    "PLAUSIBLE_SCRIPT_SRC",
    "https://plausible.io/js/pa-J6bhmMJeOSd44Xkxjn7p2.js",
).strip()

EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = _env_int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = _env_bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "josephlovesjohn@gmail.com")
CONTACT_RECIPIENT_EMAIL = os.environ.get("CONTACT_RECIPIENT_EMAIL", "josephlovesjohn@gmail.com")
LEGAL_BUSINESS_NAME = os.environ.get("LEGAL_BUSINESS_NAME", "JosephlovesJohn")
BUSINESS_CONTACT_EMAIL = os.environ.get("BUSINESS_CONTACT_EMAIL", CONTACT_RECIPIENT_EMAIL)
BUSINESS_POSTAL_ADDRESS = os.environ.get("BUSINESS_POSTAL_ADDRESS", "")
VAT_NUMBER = os.environ.get("VAT_NUMBER", "")

LOGIN_RATE_LIMIT_ATTEMPTS = _env_int("LOGIN_RATE_LIMIT_ATTEMPTS", default=5)
LOGIN_RATE_LIMIT_WINDOW = _env_int("LOGIN_RATE_LIMIT_WINDOW", default=300)
PASSWORD_RESET_RATE_LIMIT_ATTEMPTS = _env_int("PASSWORD_RESET_RATE_LIMIT_ATTEMPTS", default=5)
PASSWORD_RESET_RATE_LIMIT_WINDOW = _env_int("PASSWORD_RESET_RATE_LIMIT_WINDOW", default=3600)
CONTACT_RATE_LIMIT_ATTEMPTS = _env_int("CONTACT_RATE_LIMIT_ATTEMPTS", default=5)
CONTACT_RATE_LIMIT_WINDOW = _env_int("CONTACT_RATE_LIMIT_WINDOW", default=3600)

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").strip().upper() or "INFO"
DJANGO_LOG_LEVEL = os.environ.get("DJANGO_LOG_LEVEL", "INFO" if DEBUG else LOG_LEVEL).strip().upper() or "INFO"
DJANGO_SERVER_LOG_LEVEL = os.environ.get("DJANGO_SERVER_LOG_LEVEL", "INFO").strip().upper() or "INFO"
DJANGO_TEMPLATE_LOG_LEVEL = os.environ.get("DJANGO_TEMPLATE_LOG_LEVEL", "WARNING").strip().upper() or "WARNING"
DJANGO_DB_LOG_LEVEL = os.environ.get(
    "DJANGO_DB_LOG_LEVEL",
    "DEBUG" if _env_bool("LOG_SQL_QUERIES", default=False) else "WARNING",
).strip().upper() or "WARNING"
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": DJANGO_LOG_LEVEL,
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["console"],
            "level": DJANGO_SERVER_LOG_LEVEL,
            "propagate": False,
        },
        "django.template": {
            "handlers": ["console"],
            "level": DJANGO_TEMPLATE_LOG_LEVEL,
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": DJANGO_DB_LOG_LEVEL,
            "propagate": False,
        },
    },
}

setup_sentry_from_env()
