"""Database models for the main site app."""

from django.core.exceptions import ValidationError
from django.db import models


class OrderedGalleryAsset(models.Model):
    """Shared metadata for admin-managed artwork collections."""

    title = models.CharField(max_length=140)
    alt_text = models.CharField(max_length=180, blank=True)
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Lower numbers appear earlier on the page.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        """Model metadata for gallery ordering."""

        abstract = True
        ordering = ("sort_order", "id")

    def __str__(self):
        """Return the admin-friendly label for the asset."""
        return self.title


class GigPhoto(OrderedGalleryAsset):
    """Store editable gig photo metadata for the art gallery."""

    image_path = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional path relative to static/, for example images/gig_photos/photo.jpeg.",
    )
    image_file = models.FileField(
        upload_to="gig_photos/uploads/",
        blank=True,
        help_text="Optional file upload for the main gig photo.",
    )
    thumbnail_path = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional static thumbnail path. Falls back to the main image when blank.",
    )
    thumbnail_file = models.FileField(
        upload_to="gig_photos/thumbs/uploads/",
        blank=True,
        help_text="Optional thumbnail upload. Falls back to the main image when blank.",
    )

    class Meta(OrderedGalleryAsset.Meta):
        """Model metadata for gallery ordering."""

        verbose_name = "Gig photo"
        verbose_name_plural = "Gig photos"

    def clean(self):
        """Require either a static path or an uploaded image."""
        super().clean()
        if not self.image_path and not self.image_file:
            raise ValidationError("Add either an image upload or a static image path.")


class AlbumArt(OrderedGalleryAsset):
    """Store editable album artwork for the art gallery."""

    image_path = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional path relative to static/, for example images/album_art/cover.jpg.",
    )
    image_file = models.FileField(
        upload_to="album_art/uploads/",
        blank=True,
        help_text="Optional file upload for this album artwork.",
    )
    featured = models.BooleanField(default=False)
    fit_contain = models.BooleanField(default=False)

    class Meta(OrderedGalleryAsset.Meta):
        """Model metadata for album art ordering."""

        verbose_name = "Album art"
        verbose_name_plural = "Album art"

    def clean(self):
        """Require either a static path or an uploaded image."""
        super().clean()
        if not self.image_path and not self.image_file:
            raise ValidationError("Add either an image upload or a static image path.")


class AnimationAsset(OrderedGalleryAsset):
    """Store editable animated artwork for the art gallery."""

    class MediaKind(models.TextChoices):
        """Supported animation media types."""

        IMAGE = "image", "Image / GIF"
        VIDEO = "video", "Video"

    media_kind = models.CharField(max_length=10, choices=MediaKind.choices, default=MediaKind.IMAGE)
    file_path = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional path relative to static/, for example images/album_art/animation.gif.",
    )
    file_upload = models.FileField(
        upload_to="animations/uploads/",
        blank=True,
        help_text="Optional upload for the animation file.",
    )
    poster_path = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional poster path for video animations.",
    )
    poster_upload = models.FileField(
        upload_to="animations/posters/",
        blank=True,
        help_text="Optional poster upload for video animations.",
    )
    featured = models.BooleanField(default=False)
    fit_contain = models.BooleanField(default=False)

    class Meta(OrderedGalleryAsset.Meta):
        """Model metadata for animation ordering."""

        verbose_name = "Animation"
        verbose_name_plural = "Animations"

    def clean(self):
        """Require either a static path or an uploaded animation file."""
        super().clean()
        if not self.file_path and not self.file_upload:
            raise ValidationError("Add either an animation upload or a static file path.")
