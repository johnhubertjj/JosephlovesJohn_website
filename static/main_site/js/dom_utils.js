(function () {
    var siteUtils = window.siteUtils || {};

    siteUtils.getCookie = function (name) {
        var value = "; " + document.cookie;
        var parts = value.split("; " + name + "=");
        if (parts.length === 2) {
            return parts.pop().split(";").shift();
        }
        return "";
    };

    siteUtils.closestFromEventTarget = function (target, selector) {
        if (!target) {
            return null;
        }

        if (typeof target.closest === "function") {
            return target.closest(selector);
        }

        if (target.parentElement && typeof target.parentElement.closest === "function") {
            return target.parentElement.closest(selector);
        }

        return null;
    };

    window.siteUtils = siteUtils;
})();
