# Cloudflare R2 Setup

Cloudflare R2 is used in this project as optional storage for large public assets and private downloads.

For public site assets served through `PUBLIC_ASSET_BASE_URL`, mirror the path
inside `static/` but do not include the `static/` prefix. Mastering website
images belong under `mastering/images/`, for example:

- `mastering/images/mastering-website-header-image.webp`
- `mastering/images/john-joseph-profile.webp`
- `mastering/images/mastering-gear-rack.webp`

It can also back admin-uploaded public media files by setting:

- `MEDIA_FILES_BUCKET_NAME`
- `MEDIA_FILES_ENDPOINT_URL`
- `MEDIA_FILES_ACCESS_KEY_ID`
- `MEDIA_FILES_SECRET_ACCESS_KEY`
- `MEDIA_FILES_REGION`
- `MEDIA_FILES_BASE_URL`
- `MEDIA_FILES_KEY_PREFIX`

See [README.md](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/README.md) for the higher-level storage overview.
