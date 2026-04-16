(function () {
    var body = document.body;
    var siteUtils = window.siteUtils || {};
    var closestFromEventTarget = siteUtils.closestFromEventTarget;
    if (!body || body.getAttribute("data-analytics-enabled") !== "true") {
        return;
    }

    function getStorage() {
        try {
            return window.sessionStorage;
        } catch (error) {
            return null;
        }
    }

    function toNumber(value) {
        var parsed = window.parseFloat(value || "");
        return window.isNaN(parsed) ? 0 : parsed;
    }

    function track(eventName, options) {
        if (typeof window.plausible !== "function") {
            return;
        }

        window.plausible(eventName, options || {});
    }

    function trackOnce(key, eventName, options) {
        var storage = getStorage();
        if (storage && storage.getItem(key)) {
            return;
        }

        track(eventName, options);
        if (storage) {
            storage.setItem(key, "1");
        }
    }

    window.siteAnalytics = {
        track: track,
        trackOnce: trackOnce
    };

    document.addEventListener("click", function (event) {
        var signupOpen = closestFromEventTarget(event.target, "[data-analytics-signup-open]");
        if (signupOpen) {
            track("Signup Opened", {
                props: {
                    mode: "embed"
                }
            });
            return;
        }

        var signupFallback = closestFromEventTarget(event.target, "[data-analytics-signup-fallback]");
        if (signupFallback) {
            track("Signup Opened", {
                props: {
                    mode: "new_tab"
                }
            });
            return;
        }

        var outboundLink = closestFromEventTarget(event.target, "a[href]");
        if (!outboundLink) {
            return;
        }

        var href = outboundLink.getAttribute("href") || "";
        if (!/^https?:\/\//i.test(href)) {
            return;
        }

        var destination = "";
        try {
            destination = new URL(href, window.location.href);
        } catch (error) {
            return;
        }

        if (destination.origin === window.location.origin) {
            return;
        }

        track("Outbound Link Clicked", {
            props: {
                href: destination.href,
                host: destination.host
            }
        });
    });

    var checkout = document.querySelector("[data-analytics-begin-checkout]");
    if (checkout) {
        track("Begin Checkout", {
            props: {
                item_count: checkout.getAttribute("data-analytics-item-count") || "0",
                total_gbp: checkout.getAttribute("data-analytics-total-amount") || "0.00"
            }
        });
    }

    var purchase = document.querySelector("[data-analytics-purchase]");
    if (purchase) {
        var orderId = purchase.getAttribute("data-analytics-order-id") || "";
        trackOnce("purchase:" + orderId, "Purchase Completed", {
            props: {
                order_id: orderId,
                item_count: purchase.getAttribute("data-analytics-item-count") || "0",
                product_titles: purchase.getAttribute("data-analytics-product-titles") || ""
            },
            revenue: {
                currency: "GBP",
                amount: toNumber(purchase.getAttribute("data-analytics-total-amount"))
            }
        });
    }

    if (document.querySelector("[data-analytics-contact-success]")) {
        trackOnce("contact-success:" + window.location.pathname, "Contact Submitted");
    }
})();
