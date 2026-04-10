from django.db import models


class GigPhoto(models.Model):
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
        ordering = ("sort_order", "id")

    def __str__(self):
        return self.title
