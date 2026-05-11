(function () {
    function closestTrackLink(target) {
        if (!target) {
            return null;
        }

        if (typeof target.closest === "function") {
            return target.closest("[data-track-link-service]");
        }

        return null;
    }

    function eventPayload(link) {
        return {
            service: link.getAttribute("data-track-service") || "",
            service_label: link.getAttribute("data-track-service-label") || "",
            track_slug: link.getAttribute("data-track-slug") || "",
            track_title: link.getAttribute("data-track-title") || "",
            destination: link.getAttribute("data-track-destination") || link.href || "",
            page_path: window.location.pathname
        };
    }

    function trackPlausible(payload) {
        if (typeof window.plausible !== "function") {
            return;
        }

        window.plausible("Streaming Click", {
            props: payload
        });
    }

    function trackMeta(payload) {
        if (typeof window.fbq !== "function") {
            return;
        }

        window.fbq("trackCustom", "StreamingClick", {
            content_category: "music",
            content_name: payload.track_title,
            service: payload.service,
            service_label: payload.service_label,
            track_slug: payload.track_slug,
            track_title: payload.track_title,
            destination: payload.destination,
            page_path: payload.page_path
        });
    }

    document.addEventListener("click", function (event) {
        var link = closestTrackLink(event.target);
        if (!link) {
            return;
        }

        var payload = eventPayload(link);
        trackPlausible(payload);
        trackMeta(payload);
    });
})();
