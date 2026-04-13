(function () {
    var noticeCookieName = "site_cookie_notice";
    var noticeDismissedValue = "dismissed";

    function getCookie(name) {
        var value = "; " + document.cookie;
        var parts = value.split("; " + name + "=");
        if (parts.length === 2) {
            return parts.pop().split(";").shift();
        }
        return "";
    }

    function setDismissed() {
        document.cookie = noticeCookieName + "=" + noticeDismissedValue + "; path=/; max-age=31536000; SameSite=Lax";
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
        setBannerVisibility(getCookie(noticeCookieName) !== noticeDismissedValue);
    }

    document.addEventListener("click", function (event) {
        var dismissButton = event.target.closest("[data-cookie-dismiss]");
        if (dismissButton) {
            event.preventDefault();
            setDismissed();
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
