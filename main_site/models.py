"""Database models for the main site app."""

from django.db import models


class GigPhoto(models.Model):
    """Store editable gig photo metadata for the art gallery.

    The model lets the site owner manage live photography references through the
    Django admin without editing templates directly.
    """

    title = models.CharField(max_length=140)
    image_path = models.CharField(
        max_length=255,
        help_text="Path relative to static/, for example images/gig_photos/photo.jpeg",
    )
    thumbnail_path = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional thumbnail path relative to static/. Falls back to image_path when blank.",
    )
    alt_text = models.CharField(max_length=180, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        """Model metadata for gallery ordering."""

        ordering = ("sort_order", "id")

    def __str__(self):
        """Return the admin-friendly label for the gig photo.

        :returns: The photo title.
        :rtype: str
        """
        return self.title
