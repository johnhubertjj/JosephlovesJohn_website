(function () {
    var noticeCookieName = "site_cookie_notice";
    var preferenceCookieName = "site_cookie_preference";
    var noticeDismissedValue = "dismissed";
    var essentialOnlyValue = "essential";
    var allowOptionalValue = "all";

    function getCookie(name) {
        var value = "; " + document.cookie;
        var parts = value.split("; " + name + "=");
        if (parts.length === 2) {
            return parts.pop().split(";").shift();
        }
        return "";
    }

    function setCookie(name, value) {
        document.cookie = name + "=" + value + "; path=/; max-age=31536000; SameSite=Lax";
    }

    function applyPreferenceState(preference) {
        document.documentElement.setAttribute("data-cookie-preference", preference || "");
        document.body.setAttribute("data-cookie-preference", preference || "");
        document.dispatchEvent(
            new CustomEvent("site:cookie-preference-changed", {
                detail: { preference: preference || "" }
            })
        );
    }

    function getSavedPreference() {
        var explicitPreference = getCookie(preferenceCookieName);
        if (explicitPreference === essentialOnlyValue || explicitPreference === allowOptionalValue) {
            return explicitPreference;
        }

        // Older visits only stored that the notice was dismissed. Treat those as essential-only.
        if (getCookie(noticeCookieName) === noticeDismissedValue) {
            return essentialOnlyValue;
        }

        return "";
    }

    function savePreference(preference) {
        setCookie(preferenceCookieName, preference);
        setCookie(noticeCookieName, noticeDismissedValue);
        applyPreferenceState(preference);
    }

    function setBannerVisibility(visible) {
        var banner = document.querySelector("[data-cookie-banner]");
        if (!banner) {
            return;
        }

        banner.hidden = !visible;
        window.requestAnimationFrame(updateBannerOffset);
    }

    function updateBannerOffset() {
        var banner = document.querySelector("[data-cookie-banner]");
        var visible = !!banner && !banner.hidden;
        var height = visible ? banner.offsetHeight : 0;

        document.documentElement.style.setProperty("--cookie-banner-height", height + "px");
        document.body.classList.toggle("has-cookie-banner", visible);
    }

    function applyBannerState() {
        var preference = getSavedPreference();
        applyPreferenceState(preference);
        setBannerVisibility(!preference);
    }

    document.addEventListener("click", function (event) {
        var essentialOnlyButton = event.target.closest("[data-cookie-essential-only]");
        if (essentialOnlyButton) {
            event.preventDefault();
            savePreference(essentialOnlyValue);
            applyBannerState();
            return;
        }

        var allowOptionalButton = event.target.closest("[data-cookie-accept-all]");
        if (allowOptionalButton) {
            event.preventDefault();
            savePreference(allowOptionalValue);
            applyBannerState();
            return;
        }

        var manageButton = event.target.closest("[data-cookie-manage]");
        if (manageButton) {
            event.preventDefault();
            setBannerVisibility(true);
        }
    });

    applyBannerState();
    window.addEventListener("resize", updateBannerOffset);
})();
