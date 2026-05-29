# Search Console Checklist

Use this after deployment to give Google the clearest possible signal about the site.

## 1. Add the property

- Add `https://josephlovesjohn.com` as a property in Google Search Console.
- If you want the broadest coverage, add the domain property as well so subdomains are included.

## 2. Submit the sitemap

- Open the Sitemaps section in Search Console.
- Submit:
  - `https://josephlovesjohn.com/sitemap.xml`

## 3. Inspect the important pages

Use URL Inspection on:

- `https://josephlovesjohn.com/`
- `https://josephlovesjohn.com/music/`
- `https://josephlovesjohn.com/art/`
- `https://josephlovesjohn.com/contact/`
- `https://josephlovesjohn.com/mastering-services/`

For each page:

- check that Google can access it
- confirm the canonical URL matches the page you expect
- request indexing after launch if needed

## 4. Validate structured data

- Run the homepage and `/music/` page through Google's Rich Results Test.
- Confirm the JSON-LD is detected without errors.

## 5. Watch the first reports

After launch, review:

- Page indexing
- Sitemaps
- Manual actions
- Security issues
- Enhancements / rich result reports if Google starts surfacing them

## 6. Keep the technical basics healthy

- Make sure `SITE_URL` is set to `https://josephlovesjohn.com`
- Keep `robots.txt` publicly reachable
- Keep `sitemap.xml` returning `200`
- Avoid blocking CSS, JS, or images needed for rendering

## 7. Improve search visibility over time

- Publish clear release and gig updates on the site
- Link to the site from Spotify, Bandcamp, socials, and gig listings
- Keep page titles and meta descriptions specific to the route
- Use descriptive image alt text
- Keep the site fast and mobile-friendly

## Notes

- Structured data helps Google understand the pages better, but it does not guarantee rich results.
- Request indexing sparingly for important pages after real changes.
