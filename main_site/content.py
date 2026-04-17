"""Static content and shared constants for the main public site."""

from typing import TypedDict


class HeaderSocialLinkItem(TypedDict):
    """Typed representation of a rendered header social link."""

    href: str
    icon_class: str
    label: str


LEGAL_PAGE_CONTENT = {
    "privacy": {
        "title": "Privacy Policy",
        "eyebrow": "Privacy",
        "subtitle": "How JosephlovesJohn handles account, order, and payment-related information on this site.",
        "sections": [
            {
                "heading": "Who this policy covers",
                "paragraphs": [
                    "This website sells digital music downloads directly to listeners and also lets "
                    "visitors contact us or create an optional customer account.",
                    "The policy covers personal information collected through the website, shop "
                    "account area, checkout flow, and contact forms.",
                ],
            },
            {
                "heading": "Information we collect",
                "bullets": [
                    "Account details such as username, name, and email address.",
                    "Order records such as purchased tracks, totals, timestamps, and download entitlements.",
                    "Payment-related references such as Stripe Checkout Session IDs and Payment Intent IDs.",
                    "Messages you send through the contact form or support requests.",
                    "Technical data needed to keep the site secure and remember cart, login, and cookie preferences.",
                ],
            },
            {
                "heading": "How we use it",
                "bullets": [
                    "To create and manage customer accounts.",
                    "To process orders, verify payment, and provide download access.",
                    "To answer enquiries and support requests.",
                    "To maintain site security, prevent misuse, and keep records required for "
                    "accounting or legal obligations.",
                    "To send marketing only where you have actively opted in.",
                ],
            },
            {
                "heading": "Payments and third parties",
                "paragraphs": [
                    "Payments are processed through Stripe on Stripe-hosted checkout pages. This "
                    "website does not store full card details.",
                    "We share only the information needed to create, verify, and record a payment, "
                    "including your order reference, email address where available, and the items "
                    "being purchased.",
                ],
            },
            {
                "heading": "Retention and your choices",
                "paragraphs": [
                    "We keep order and account information for as long as needed to provide "
                    "downloads, maintain business records, and meet legal or tax obligations.",
                    "You can contact us to request access, correction, or deletion of personal "
                    "information, subject to any records we must keep by law.",
                ],
            },
        ],
    },
    "cookies": {
        "title": "Cookies Policy",
        "eyebrow": "Cookies",
        "subtitle": "How this site uses essential cookies and optional third-party embeds.",
        "sections": [
            {
                "heading": "Essential cookies",
                "paragraphs": [
                    "This site uses essential cookies and similar storage to keep the shop working. "
                    "That includes remembering your cart, maintaining login sessions, protecting "
                    "forms with CSRF tokens, and saving your cookie preference.",
                    "These cookies are needed for services you have asked for, so they load automatically.",
                ],
            },
            {
                "heading": "Optional cookies and embedded services",
                "paragraphs": [
                    "The mailing-list signup embed uses a third-party service. Optional cookies are "
                    "blocked until you allow them.",
                    "You can still use the direct signup link without enabling optional cookies on this site.",
                ],
            },
            {
                "heading": "Stripe and payment pages",
                "paragraphs": [
                    "When you continue to Stripe Checkout, you move to Stripe-hosted pages. Stripe "
                    "may use its own cookies and privacy controls under its own policies.",
                ],
            },
            {
                "heading": "Managing cookies",
                "paragraphs": [
                    "Use the cookie controls on this site to accept optional cookies or keep essential-only mode.",
                    "You can also clear cookies in your browser settings, though doing so may remove "
                    "your cart, login session, and saved site preferences.",
                ],
            },
        ],
    },
    "terms": {
        "title": "Terms of Sale",
        "eyebrow": "Terms",
        "subtitle": "The basic terms that apply when you buy digital music downloads from this website.",
        "sections": [
            {
                "heading": "What you are buying",
                "paragraphs": [
                    "Products sold through this shop are digital music downloads. No physical goods are shipped.",
                    "Prices are shown in GBP. Shipping does not apply to digital downloads.",
                ],
            },
            {
                "heading": "Checkout and payment",
                "paragraphs": [
                    "Orders are placed through Stripe-hosted checkout pages. Payment must be "
                    "confirmed before download access is unlocked.",
                    "Where VAT becomes applicable, checkout and order records should reflect the "
                    "price charged and any required tax treatment.",
                    "The mailing-list signup form is treated as an essential embedded service when "
                    "you choose to use it, because the provider needs cookies or similar storage to "
                    "render and submit the form correctly.",
                ],
            },
            {
                "heading": "Accounts and download access",
                "paragraphs": [
                    "You can buy as a guest or create an account. Logged-in customers can review "
                    "previous confirmed purchases in their account area.",
                    "Download access is provided after payment confirmation and may be limited if "
                    "misuse, fraud, or abuse is detected.",
                ],
            },
            {
                "heading": "Contact and support",
                "paragraphs": [
                    "If you have trouble receiving or using a download, contact us and we will "
                    "investigate and help put it right.",
                ],
            },
        ],
    },
    "refunds": {
        "title": "Refunds and Digital Downloads",
        "eyebrow": "",
        "subtitle": "Important information about cancellation rights and support for digital music downloads.",
        "sections": [
            {
                "heading": "Immediate digital supply",
                "paragraphs": [
                    "By continuing to payment for a digital download, you confirm that supply should "
                    "begin immediately after payment is confirmed.",
                    "Once immediate supply begins, the usual 14-day cancellation right for distance "
                    "sales no longer applies to that digital content.",
                ],
            },
            {
                "heading": "When to contact us",
                "bullets": [
                    "A file does not download after payment confirmation.",
                    "A download is corrupted or materially not as described.",
                    "You were charged more than expected or experienced a duplicate payment.",
                ],
            },
            {
                "heading": "How we handle issues",
                "paragraphs": [
                    "Where there is a genuine delivery, quality, or billing problem, we will review "
                    "the order and aim to provide a replacement download, correction, or refund where "
                    "appropriate.",
                ],
            },
        ],
    },
}

LEGAL_PAGE_ORDER = ("privacy", "cookies", "terms", "refunds")

SPOTIFY_SOCIAL_LINK: HeaderSocialLinkItem = {
    "href": "https://open.spotify.com/artist/27YZiLsfuwfBI5e4BZyTIi?si=rcYZFzPzSPCfartpPGM6gg",
    "icon_class": "icon brands fa-spotify",
    "label": "Spotify",
}
