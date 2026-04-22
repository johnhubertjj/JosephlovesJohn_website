"""Custom storage backends used by the JosephlovesJohn project."""

from __future__ import annotations

import mimetypes
from datetime import datetime
from io import BytesIO
from urllib.parse import urljoin

from django.conf import settings
from django.core.files.base import File
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible

from josephlovesjohn_site.assets import normalize_asset_path


@deconstructible
class S3CompatibleMediaStorage(Storage):
    """Store uploaded media files in an S3-compatible public bucket."""

    def __init__(self) -> None:
        self.bucket_name = settings.MEDIA_FILES_BUCKET_NAME
        self.endpoint_url = settings.MEDIA_FILES_ENDPOINT_URL
        self.access_key_id = settings.MEDIA_FILES_ACCESS_KEY_ID
        self.secret_access_key = settings.MEDIA_FILES_SECRET_ACCESS_KEY
        self.region = settings.MEDIA_FILES_REGION
        self.base_url = settings.MEDIA_FILES_BASE_URL
        self.key_prefix = settings.MEDIA_FILES_KEY_PREFIX
        self._client = None

    @property
    def client(self):
        """Return a lazily-created boto3 client."""
        if self._client is None:
            try:
                import boto3  # type: ignore[import-untyped]
            except ImportError as exc:  # pragma: no cover - exercised only when dependency is missing.
                raise RuntimeError("boto3 is required for object-storage media uploads.") from exc

            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name=self.region,
            )
        return self._client

    def _normalize_name(self, name: str) -> str:
        normalized = normalize_asset_path(name)
        if not normalized:
            raise ValueError("Uploaded media paths must not be blank.")
        return normalized

    def _object_key(self, name: str) -> str:
        normalized = self._normalize_name(name)
        return f"{self.key_prefix}/{normalized}" if self.key_prefix else normalized

    def _open(self, name: str, mode: str = "rb") -> File:
        if "r" not in mode:
            raise ValueError("This storage backend only supports read modes when opening files.")

        response = self.client.get_object(
            Bucket=self.bucket_name,
            Key=self._object_key(name),
        )
        return File(BytesIO(response["Body"].read()), name=name)

    def _save(self, name: str, content) -> str:
        name = self.get_available_name(self._normalize_name(name), max_length=getattr(content, "max_length", None))
        body = content.read()
        extra_args: dict[str, str] = {}
        content_type = getattr(content, "content_type", "") or mimetypes.guess_type(name)[0] or ""
        if content_type:
            extra_args["ContentType"] = content_type

        self.client.put_object(
            Bucket=self.bucket_name,
            Key=self._object_key(name),
            Body=body,
            **extra_args,
        )
        return name

    def delete(self, name: str) -> None:
        self.client.delete_object(
            Bucket=self.bucket_name,
            Key=self._object_key(name),
        )

    def exists(self, name: str) -> bool:
        try:
            self.client.head_object(
                Bucket=self.bucket_name,
                Key=self._object_key(name),
            )
        except Exception:
            return False
        return True

    def size(self, name: str) -> int:
        response = self.client.head_object(
            Bucket=self.bucket_name,
            Key=self._object_key(name),
        )
        return int(response.get("ContentLength", 0))

    def url(self, name: str | None) -> str:
        if not name:
            raise ValueError("Set a file name before requesting an object-storage media URL.")

        base_url = self.base_url.strip().rstrip("/")
        if not base_url and str(settings.MEDIA_URL).startswith(("http://", "https://", "//")):
            base_url = str(settings.MEDIA_URL).strip().rstrip("/")
        if not base_url:
            raise ValueError("Set MEDIA_FILES_BASE_URL to generate URLs for object-stored uploads.")
        base_url = base_url + "/"
        return urljoin(base_url, self._normalize_name(name))

    def get_modified_time(self, name: str) -> datetime:
        response = self.client.head_object(
            Bucket=self.bucket_name,
            Key=self._object_key(name),
        )
        last_modified = response.get("LastModified")
        if not isinstance(last_modified, datetime):
            raise NotImplementedError("The storage provider did not return a modified timestamp.")
        return last_modified
