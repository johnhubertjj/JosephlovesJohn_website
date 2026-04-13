(function () {
    var consentCookieName = "site_cookie_consent";
    var consentAcceptedValue = "accepted";
    var consentRejectedValue = "essential";

    function getCookie(name) {
        var value = "; " + document.cookie;
        var parts = value.split("; " + name + "=");
        if (parts.length === 2) {
            return parts.pop().split(";").shift();
        }
        return "";
    }

    function setConsent(value) {
        document.cookie = consentCookieName + "=" + value + "; path=/; max-age=31536000; SameSite=Lax";
    }

    function getConsent() {
        return getCookie(consentCookieName);
    }

    function setBannerVisibility(visible) {
        var banner = document.querySelector("[data-cookie-banner]");
        if (!banner) {
            return;
        }

        banner.hidden = !visible;
    }

    function loadOptionalEmbeds() {
        document.querySelectorAll("[data-cookie-src]").forEach(function (container) {
            if (container.getAttribute("data-cookie-loaded") === "true") {
                return;
            }

            var src = container.getAttribute("data-cookie-src");
            if (!src) {
                return;
            }

            var script = document.createElement("script");
            script.async = true;
            script.src = src;
            container.appendChild(script);
            container.setAttribute("data-cookie-loaded", "true");

            var wrapper = container.closest(".intro-signup-form");
            if (wrapper) {
                wrapper.classList.add("is-loaded");
            }
        });
    }

    function applyConsent() {
        var consent = getConsent();
        if (consent === consentAcceptedValue) {
            loadOptionalEmbeds();
            setBannerVisibility(false);
            return;
        }

        if (consent === consentRejectedValue) {
            setBannerVisibility(false);
            return;
        }

        setBannerVisibility(true);
    }

    document.addEventListener("click", function (event) {
        var acceptButton = event.target.closest("[data-cookie-accept]");
        if (acceptButton) {
            event.preventDefault();
            setConsent(consentAcceptedValue);
            applyConsent();
            return;
        }

        var rejectButton = event.target.closest("[data-cookie-reject]");
        if (rejectButton) {
            event.preventDefault();
            setConsent(consentRejectedValue);
            applyConsent();
            return;
        }

        var manageButton = event.target.closest("[data-cookie-manage]");
        if (manageButton) {
            event.preventDefault();
            setBannerVisibility(true);
        }
    });

    applyConsent();
})();
