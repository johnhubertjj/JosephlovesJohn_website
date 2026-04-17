"""Shared pytest fixtures and test controls for the JosephlovesJohn suite."""

import os
from decimal import Decimal
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
def media_base_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point uploaded media helpers at a temporary media directory."""
    media_dir = tmp_path / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(main_site_views.settings, "MEDIA_ROOT", media_dir, raising=False)
    monkeypatch.setattr(main_site_views.settings, "MEDIA_URL", "/media/", raising=False)
    return media_dir


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


@pytest.fixture
def create_media_asset(media_base_dir: Path):
    """Create a temporary uploaded-media asset and return its relative path."""

    def _create(relative_path: str, content: bytes = b"asset") -> str:
        target = media_base_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return relative_path

    return _create


@pytest.fixture
def private_downloads_base_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point private download helpers at a temporary download directory."""
    downloads_dir = tmp_path / "private_downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(main_site_views.settings, "PRIVATE_DOWNLOADS_ROOT", downloads_dir, raising=False)
    return downloads_dir


@pytest.fixture
def create_private_download_asset(private_downloads_base_dir: Path):
    """Create a temporary private download asset and return its relative path."""

    def _create(relative_path: str, content: bytes = b"download") -> str:
        target = private_downloads_base_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return relative_path

    return _create


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register project-specific pytest command-line options.

    :param parser: The pytest parser used to define custom flags.
    :type parser: pytest.Parser
    """
    parser.addoption(
        "--run-browser",
        action="store_true",
        default=False,
        help="Run Playwright-backed browser tests.",
    )
    parser.addoption(
        "--browser-engine",
        action="store",
        default=os.environ.get("PLAYWRIGHT_BROWSER_ENGINE", "chromium"),
        choices=("chromium", "firefox", "webkit"),
        help="Browser engine for Playwright-backed tests.",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip browser tests unless the caller opts in explicitly.

    :param config: Active pytest configuration.
    :type config: pytest.Config
    :param items: Collected test items for the current run.
    :type items: list[pytest.Item]
    """
    if config.getoption("--run-browser"):
        return

    skip_browser = pytest.mark.skip(reason="Browser tests require --run-browser.")
    for item in items:
        if "browser" in item.keywords:
            item.add_marker(skip_browser)


def pytest_configure(config: pytest.Config) -> None:
    """Apply pytest-time environment tweaks for browser-mode runs.

    :param config: Active pytest configuration.
    :type config: pytest.Config
    """
    if config.getoption("--run-browser"):
        os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")


@pytest.fixture(autouse=True)
def ensure_seeded_shop_products(request: pytest.FixtureRequest) -> None:
    """Keep the demo storefront products available for DB-backed tests.

    :param request: Active pytest fixture request.
    :type request: pytest.FixtureRequest
    :returns: ``None``.
    :rtype: None
    """
    if not (
        request.node.get_closest_marker("django_db")
        or request.node.get_closest_marker("browser")
    ):
        return

    request.getfixturevalue("db")
    from shop.models import Product

    seed_payloads = (
        {
            "title": "Dark and Light - Artist Version",
            "slug": "dark-and-light-artist-version",
            "artist_name": "JosephlovesJohn and Jayne Connell",
            "meta": "Single",
            "description": "Original artist version of Dark and Light.",
            "art_path": "images/album_art/dark_and_light_artist_cover.jpg",
            "art_alt": "Dark and Light artist cover artwork",
            "preview_file_wav": "audio/dark_and_light_final_full_mastered_new_deesser3_24bit_192khz_JJ.wav",
            "preview_file_mp3": "audio/dark_and_light_final_full_mastered_new_deesser3_24bit_192khz_JJ.mp3",
            "download_file_path": "audio/dark_and_light_final_full_mastered_new_deesser3_24bit_192khz_JJ.mp3",
            "download_file_wav_path": "audio/dark_and_light_final_full_mastered_new_deesser3_24bit_192khz_JJ.wav",
            "price": Decimal("1.00"),
            "sort_order": 1,
            "is_reversed": False,
        },
        {
            "title": "Dark and Light - Instrumental",
            "slug": "dark-and-light-instrumental",
            "artist_name": "JosephlovesJohn and Jayne Connell",
            "meta": "Instrumental Mix",
            "description": "Instrumental mix of Dark and Light.",
            "art_path": "images/album_art/dark_and_light_instrumental.jpg",
            "art_alt": "Dark and Light instrumental artwork",
            "preview_file_wav": "audio/dark_and_light_final_instrumental_v3_24_192.wav",
            "preview_file_mp3": "audio/dark_and_light_final_instrumental_v3_24_192.mp3",
            "download_file_path": "audio/dark_and_light_final_instrumental_v3_24_192.mp3",
            "download_file_wav_path": "audio/dark_and_light_final_instrumental_v3_24_192.wav",
            "price": Decimal("1.00"),
            "sort_order": 2,
            "is_reversed": True,
        },
    )

    for payload in seed_payloads:
        Product.objects.update_or_create(slug=payload["slug"], defaults=payload)


@pytest.fixture(autouse=True)
def ensure_browser_gallery_assets(request: pytest.FixtureRequest, create_static_asset) -> None:
    """Keep at least one art-gallery lightbox item available for browser tests."""
    if not request.node.get_closest_marker("browser"):
        return

    request.getfixturevalue("db")
    from main_site.models import AlbumArt, GigPhoto

    gig_image = create_static_asset("images/gig_photos/browser-gig-photo.jpg")
    gig_thumbnail = create_static_asset("images/gig_photos/thumbs/browser-gig-thumb.jpg")
    album_image = create_static_asset("images/album_art/browser-album-art.jpg")

    GigPhoto.objects.update_or_create(
        title="Browser Gig Photo",
        defaults={
            "image_path": gig_image,
            "thumbnail_path": gig_thumbnail,
            "alt_text": "Browser gig photo",
            "sort_order": 0,
            "is_active": True,
        },
    )
    AlbumArt.objects.update_or_create(
        title="Browser Album Art",
        defaults={
            "image_path": album_image,
            "alt_text": "Browser album artwork",
            "featured": True,
            "sort_order": 0,
            "is_active": True,
        },
    )


def _browser_executable_candidates(browser_engine_name: str) -> tuple[str, ...]:
    """Return likely browser executables for local runs.

    :returns: Candidate executable paths to try before bundled Playwright browsers.
    :rtype: tuple[str, ...]
    """
    if browser_engine_name == "firefox":
        candidates = [
            os.environ.get("PLAYWRIGHT_FIREFOX_EXECUTABLE"),
        ]
        return tuple(candidate for candidate in candidates if candidate)

    if browser_engine_name == "webkit":
        candidates = [
            os.environ.get("PLAYWRIGHT_WEBKIT_EXECUTABLE"),
        ]
        return tuple(candidate for candidate in candidates if candidate)

    candidates = [
        os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ]
    return tuple(candidate for candidate in candidates if candidate)


@pytest.fixture(scope="session")
def browser_engine_name(request: pytest.FixtureRequest) -> str:
    """Return the configured Playwright browser engine name."""
    return str(request.config.getoption("--browser-engine"))


@pytest.fixture(scope="session")
def browser_launch_options(browser_engine_name: str) -> dict[str, object]:
    """Build launch options for Playwright browser sessions.

    :returns: Chromium launch keyword arguments tuned for local and CI usage.
    :rtype: dict[str, object]
    """
    launch_options: dict[str, object] = {"headless": True}
    if browser_engine_name == "chromium":
        launch_options["args"] = ["--disable-dev-shm-usage", "--no-sandbox"]

    for candidate in _browser_executable_candidates(browser_engine_name):
        if Path(candidate).exists():
            launch_options["executable_path"] = candidate
            break

    return launch_options


@pytest.fixture(scope="session")
def playwright_browser(browser_engine_name: str, browser_launch_options: dict[str, object]):
    """Launch a reusable Chromium session for browser-marked tests.

    :param browser_launch_options: Browser launch keyword arguments.
    :type browser_launch_options: dict[str, object]
    :yields: A Playwright browser instance.
    """
    sync_api = pytest.importorskip("playwright.sync_api", reason="playwright is required for browser tests")

    with sync_api.sync_playwright() as playwright:
        try:
            browser_type = getattr(playwright, browser_engine_name)
            browser = browser_type.launch(**browser_launch_options)
        except Exception as exc:  # pragma: no cover - exercised only when browser launch fails.
            pytest.skip(f"Browser tests require a runnable {browser_engine_name} browser: {exc}")

        try:
            yield browser
        finally:
            browser.close()


@pytest.fixture
def browser_page(playwright_browser):
    """Create an isolated Playwright page and fail on uncaught page errors.

    :param playwright_browser: Session-scoped browser instance.
    :yields: A fresh Playwright page for the current test.
    """
    context = playwright_browser.new_context(
        viewport={"width": 1440, "height": 960},
        accept_downloads=True,
    )
    page = context.new_page()
    page.set_default_timeout(20_000)
    page_errors: list[str] = []
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))

    try:
        yield page
    finally:
        context.close()
        assert not page_errors, f"Unexpected browser page errors: {page_errors}"
