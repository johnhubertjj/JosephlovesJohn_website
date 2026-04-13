"""Helpers for protected paid-download delivery."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponseRedirect
from josephlovesjohn_site.assets import is_external_url, normalize_asset_path


def _private_object_key(relative_path: str, *, key_prefix: str) -> str:
    """Build an object key used for private storage."""
    normalized = normalize_asset_path(relative_path)
    if not normalized:
        raise Http404("Download not found")
    return f"{key_prefix}/{normalized}" if key_prefix else normalized


def _r2_client(*, endpoint_url: str, access_key_id: str, secret_access_key: str, region: str):
    """Build an R2-compatible S3 client."""
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover - exercised only when dependency is missing.
        raise RuntimeError("boto3 is required for private R2 links.") from exc

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=region,
    )


def presigned_private_asset_url(
    relative_path: str,
    *,
    bucket_name: str,
    endpoint_url: str,
    access_key_id: str,
    secret_access_key: str,
    region: str,
    key_prefix: str = "",
    expires_in: int = 300,
    download_name: str | None = None,
) -> str:
    """Build a short-lived presigned URL for a private R2 object."""
    if not (bucket_name and endpoint_url and access_key_id and secret_access_key):
        raise Http404("Private storage is not configured")

    client = _r2_client(
        endpoint_url=endpoint_url,
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
        region=region,
    )
    params = {
        "Bucket": bucket_name,
        "Key": _private_object_key(relative_path, key_prefix=key_prefix),
    }
    if download_name:
        params["ResponseContentDisposition"] = f'attachment; filename="{download_name}"'

    return client.generate_presigned_url(
        "get_object",
        Params=params,
        ExpiresIn=max(expires_in, 1),
    )


def _local_download_response(relative_path: str, *, download_name: str) -> FileResponse:
    """Stream a private local file from the configured download root."""
    normalized = normalize_asset_path(relative_path)
    if not normalized or is_external_url(normalized):
        raise Http404("Download not found")

    root = Path(settings.PRIVATE_DOWNLOADS_ROOT).resolve()
    candidate = (root / normalized).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise Http404("Download not found") from exc

    if not candidate.is_file():
        raise Http404("Download not found")

    content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
    return FileResponse(
        candidate.open("rb"),
        as_attachment=True,
        filename=download_name,
        content_type=content_type,
    )


def build_download_response(relative_path: str, *, download_name: str):
    """Return either a presigned redirect or a local file response."""
    if is_external_url(relative_path):
        return HttpResponseRedirect(relative_path)

    if settings.PRIVATE_DOWNLOADS_BUCKET_NAME:
        return HttpResponseRedirect(
            presigned_private_asset_url(
                relative_path,
                bucket_name=settings.PRIVATE_DOWNLOADS_BUCKET_NAME,
                endpoint_url=settings.PRIVATE_DOWNLOADS_ENDPOINT_URL,
                access_key_id=settings.PRIVATE_DOWNLOADS_ACCESS_KEY_ID,
                secret_access_key=settings.PRIVATE_DOWNLOADS_SECRET_ACCESS_KEY,
                region=settings.PRIVATE_DOWNLOADS_REGION,
                key_prefix=settings.PRIVATE_DOWNLOADS_KEY_PREFIX,
                expires_in=settings.PRIVATE_DOWNLOADS_URL_EXPIRY,
                download_name=download_name,
            )
        )

    return _local_download_response(relative_path, download_name=download_name)


def preview_asset_url(relative_path: str) -> str:
    """Return a signed preview URL when private preview storage is configured."""
    if is_external_url(relative_path):
        return relative_path
    if not settings.PRIVATE_PREVIEWS_BUCKET_NAME:
        raise Http404("Private preview storage is not configured")

    return presigned_private_asset_url(
        relative_path,
        bucket_name=settings.PRIVATE_PREVIEWS_BUCKET_NAME,
        endpoint_url=settings.PRIVATE_PREVIEWS_ENDPOINT_URL,
        access_key_id=settings.PRIVATE_PREVIEWS_ACCESS_KEY_ID,
        secret_access_key=settings.PRIVATE_PREVIEWS_SECRET_ACCESS_KEY,
        region=settings.PRIVATE_PREVIEWS_REGION,
        key_prefix=settings.PRIVATE_PREVIEWS_KEY_PREFIX,
        expires_in=settings.PRIVATE_PREVIEWS_URL_EXPIRY,
    )
