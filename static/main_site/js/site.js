(function () {
    var body = document.body;
    if (!body) {
        return;
    }

    var ua = navigator.userAgent || "";
    var vendor = navigator.vendor || "";
    var isSafari = vendor.indexOf("Apple") !== -1
        && ua.indexOf("CriOS") === -1
        && ua.indexOf("Chrome") === -1
        && ua.indexOf("Chromium") === -1
        && ua.indexOf("Edg") === -1
        && ua.indexOf("OPR") === -1
        && ua.indexOf("FxiOS") === -1;

    if (isSafari) {
        body.classList.add("is-safari-browser");
    }
})();

(function () {
    var validSections = ["intro", "music", "art", "contact"];

    function normalizeSectionHash() {
        var currentHash = window.location.hash || "";
        if (!currentHash || currentHash === "#") {
            return;
        }

        var section = currentHash.replace(/^#/, "");
        if (section.indexOf("/") === -1) {
            return;
        }

        var normalizedSection = "";
        section.split("/").forEach(function (segment) {
            if (validSections.indexOf(segment) !== -1) {
                normalizedSection = segment;
            }
        });

        if (!normalizedSection) {
            return;
        }

        var normalizedHash = "#" + normalizedSection;
        if (normalizedHash === currentHash) {
            return;
        }

        window.history.replaceState(
            null,
            "",
            window.location.pathname + window.location.search + normalizedHash
        );
    }

    normalizeSectionHash();
    window.addEventListener("pageshow", normalizeSectionHash);
    window.addEventListener("hashchange", normalizeSectionHash);
})();

(function () {
    function getActiveArticle() {
        return document.querySelector("#main article.active");
    }

    document.addEventListener(
        "click",
        function (event) {
            if (!(event.target instanceof Element)) {
                return;
            }

            var link = event.target.closest("a[target='_blank']");
            var currentHash = window.location.hash || "";
            if (!link || (currentHash && currentHash !== "#")) {
                return;
            }

            var activeArticle = getActiveArticle();
            if (!activeArticle || !activeArticle.id || !activeArticle.contains(link)) {
                return;
            }

            var href = link.getAttribute("href") || "";
            if (!href || href.charAt(0) === "#") {
                return;
            }

            // Preserve the active section before a popup/new-tab jump so
            // hash-based navigation resumes from a single valid article id.
            window.history.replaceState(
                null,
                "",
                window.location.pathname + window.location.search + "#" + activeArticle.id
            );
        },
        true
    );
})();

(function () {
    var authEntry = document.querySelector("[data-music-auth-entry]");
    var body = document.body;
    var main = document.getElementById("main");
    var wrapper = document.getElementById("wrapper");
    if (!authEntry) {
        return;
    }

    var routeSection = (wrapper && wrapper.getAttribute("data-route-section")) || "main";

    function getActiveArticle() {
        return document.querySelector("#main article.active");
    }

    function syncMusicAuthEntry() {
        var activeArticle = getActiveArticle();
        var isMusicVisible = !!(activeArticle && activeArticle.id === "music");

        if (
            !isMusicVisible
            && routeSection === "music"
            && window.location.hash === "#music"
            && !body.classList.contains("is-article-visible")
        ) {
            isMusicVisible = true;
        }

        authEntry.classList.toggle("is-hidden", !isMusicVisible);
        authEntry.setAttribute("aria-hidden", isMusicVisible ? "false" : "true");
    }

    window.addEventListener("hashchange", syncMusicAuthEntry);
    if (main) {
        new MutationObserver(syncMusicAuthEntry).observe(main, {
            subtree: true,
            attributes: true,
            attributeFilter: ["class"],
        });
    }
    new MutationObserver(syncMusicAuthEntry).observe(body, {
        attributes: true,
        attributeFilter: ["class"],
    });
    syncMusicAuthEntry();
})();

(function () {
    var signupRoot = document.querySelector("[data-signup-root]");
    if (!signupRoot) {
        return;
    }

    var signupGate = signupRoot.querySelector("[data-signup-gate]");
    var signupEmbed = signupRoot.querySelector("[data-signup-embed]");
    var openButton = signupRoot.querySelector("[data-signup-open]");
    var kitSrc = signupRoot.getAttribute("data-kit-src") || "";
    var kitLoaded = false;

    function getCookiePreference() {
        return document.documentElement.getAttribute("data-cookie-preference") || "";
    }

    function styleKitSignup() {
        var submitButton = signupRoot.querySelector(".formkit-submit");
        var emailInput = signupRoot.querySelector(".formkit-input");

        if (submitButton) {
            submitButton.classList.add("primary", "music-accent-button", "button");
        }

        if (emailInput && !emailInput.getAttribute("placeholder")) {
            emailInput.setAttribute("placeholder", "Your email address");
        }
    }

    function resetOpenButton() {
        if (!openButton) {
            return;
        }

        openButton.disabled = false;
        openButton.textContent = "Open signup form";
    }

    function teardownKitSignup() {
        if (!signupEmbed) {
            return;
        }

        signupEmbed.innerHTML = "";
        signupEmbed.hidden = true;
        kitLoaded = false;
        signupRoot.classList.remove("is-loading-signup", "is-signup-live");
        if (signupGate) {
            signupGate.hidden = false;
        }
        resetOpenButton();
    }

    function loadKitSignup() {
        if (kitLoaded || !signupEmbed || !kitSrc) {
            return;
        }

        kitLoaded = true;
        signupRoot.classList.add("is-loading-signup");
        signupEmbed.hidden = false;

        if (openButton) {
            openButton.disabled = true;
            openButton.textContent = "Loading form";
        }

        var script = document.createElement("script");
        script.async = true;
        script.src = kitSrc;
        script.setAttribute("data-uid", "408ee57c19");
        signupEmbed.appendChild(script);
    }

    if (openButton) {
        openButton.addEventListener("click", function () {
            loadKitSignup();
        });
    }

    document.addEventListener("site:cookie-preference-changed", function (event) {
        if (!event.detail) {
            return;
        }

        if (event.detail.preference === "all") {
            loadKitSignup();
            return;
        }

        teardownKitSignup();
    });

    if (getCookiePreference() === "all") {
        loadKitSignup();
    } else {
        teardownKitSignup();
    }

    new MutationObserver(function () {
        styleKitSignup();

        if (!signupRoot.querySelector(".formkit-form, .seva-form")) {
            return;
        }

        signupRoot.classList.remove("is-loading-signup");
        signupRoot.classList.add("is-signup-live");
        if (signupGate) {
            signupGate.hidden = true;
        }
    }).observe(signupRoot, {
        childList: true,
        subtree: true
    });
})();

(function () {
    var musicArticle = document.getElementById("music");
    if (!musicArticle) {
        return;
    }

    var frames = musicArticle.querySelectorAll(".music-player-frame");
    var shellWrapper = document.getElementById("wrapper");
    var playerScriptPromise = null;
    var playersInitialized = false;
    var playerScriptPath = (shellWrapper && shellWrapper.getAttribute("data-playerjs-src")) || "";

    function loadPlayerJs() {
        if (typeof Playerjs !== "undefined") {
            return Promise.resolve(true);
        }

        if (!playerScriptPath) {
            return Promise.resolve(false);
        }

        if (playerScriptPromise) {
            return playerScriptPromise;
        }

        playerScriptPromise = new Promise(function (resolve) {
            var existingScript = document.querySelector('script[data-playerjs-script="true"]');
            if (existingScript) {
                existingScript.addEventListener("load", function () {
                    resolve(typeof Playerjs !== "undefined");
                });
                existingScript.addEventListener("error", function () {
                    resolve(false);
                });
                return;
            }

            var script = document.createElement("script");
            script.src = playerScriptPath;
            script.async = true;
            script.setAttribute("data-playerjs-script", "true");
            script.addEventListener("load", function () {
                resolve(typeof Playerjs !== "undefined");
            });
            script.addEventListener("error", function () {
                resolve(false);
            });
            document.body.appendChild(script);
        });

        return playerScriptPromise;
    }

    function shouldPreferCompressedAudio() {
        var connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
        if (!connection) {
            return true;
        }

        if (connection.saveData) {
            return true;
        }

        var type = (connection.effectiveType || "").toLowerCase();
        if (type && type !== "4g") {
            return true;
        }

        if (typeof connection.downlink === "number" && connection.downlink > 0 && connection.downlink < 6) {
            return true;
        }

        if (typeof connection.rtt === "number" && connection.rtt > 300) {
            return true;
        }

        return !(type === "4g" && typeof connection.downlink === "number" && connection.downlink >= 6);
    }

    function pickPreferredAudioFile(frame) {
        var wav = frame.getAttribute("data-file-wav") || "";
        var mp3 = frame.getAttribute("data-file-mp3") || "";
        var preferCompressed = shouldPreferCompressedAudio();

        if (preferCompressed && mp3) {
            return mp3;
        }

        if (wav) {
            return wav;
        }

        return mp3;
    }

    function getAudioMimeType(path) {
        var cleanPath = (path || "").split("?")[0].toLowerCase();

        if (cleanPath.endsWith(".wav")) {
            return "audio/wav";
        }
        if (cleanPath.endsWith(".mp3")) {
            return "audio/mpeg";
        }
        if (cleanPath.endsWith(".ogg")) {
            return "audio/ogg";
        }
        if (cleanPath.endsWith(".m4a") || cleanPath.endsWith(".mp4")) {
            return "audio/mp4";
        }
        return "audio/*";
    }

    function hidePlayerTitlePlaceholder(frame) {
        var attempts = 0;
        var maxAttempts = 45;
        var timer = setInterval(function () {
            attempts += 1;
            var iframe = frame.querySelector("iframe");

            if (!iframe) {
                if (attempts >= maxAttempts) {
                    clearInterval(timer);
                }
                return;
            }

            try {
                var doc = iframe.contentDocument || iframe.contentWindow.document;
                if (!doc || !doc.body) {
                    if (attempts >= maxAttempts) {
                        clearInterval(timer);
                    }
                    return;
                }

                var found = false;
                var nodes = doc.body.querySelectorAll("*");
                nodes.forEach(function (node) {
                    if (node.children.length > 0) {
                        return;
                    }
                    if ((node.textContent || "").trim() === "Title - Song") {
                        node.style.display = "none";
                        found = true;
                    }
                });

                if (found || attempts >= maxAttempts) {
                    clearInterval(timer);
                }
            } catch (error) {
                clearInterval(timer);
            }
        }, 150);
    }

    function primePlayerMetadata(frame) {
        var attempts = 0;
        var maxAttempts = 80;
        var timer = setInterval(function () {
            attempts += 1;

            var iframe = frame.querySelector("iframe");
            if (!iframe) {
                if (attempts >= maxAttempts) {
                    clearInterval(timer);
                }
                return;
            }

            try {
                var doc = iframe.contentDocument || iframe.contentWindow.document;
                if (!doc || !doc.body) {
                    return;
                }

                var media = doc.querySelector("audio, video");
                if (!media) {
                    if (attempts >= maxAttempts) {
                        clearInterval(timer);
                    }
                    return;
                }

                media.preload = "auto";
                if (!media.dataset.metadataPrimed) {
                    media.dataset.metadataPrimed = "1";
                    media.load();
                }

                if (isFinite(media.duration) && media.duration > 0) {
                    clearInterval(timer);
                } else if (attempts >= maxAttempts) {
                    clearInterval(timer);
                }
            } catch (error) {
                clearInterval(timer);
            }
        }, 125);
    }

    function renderFrame(frame, canUsePlayerjs) {
        var file = pickPreferredAudioFile(frame);
        if (!file) {
            return;
        }

        if (frame.dataset.playerReady === "1") {
            return;
        }

        frame.dataset.playerReady = "1";

        if (canUsePlayerjs) {
            try {
                new Playerjs({
                    id: frame.id,
                    file: file,
                    title: " ",
                    preloading: 1,
                    disablePreload: 0,
                    showuntilmeta: 1
                });
                frame.classList.add("is-enhanced");
                hidePlayerTitlePlaceholder(frame);
                primePlayerMetadata(frame);
                return;
            } catch (error) {
                // Fallback below if PlayerJS initialization fails.
            }
        }

        frame.innerHTML =
            '<audio class="music-player-fallback" controls preload="metadata">' +
            '<source src="' + file + '" type="' + getAudioMimeType(file) + '">' +
            "</audio>";
        frame.classList.add("is-enhanced");
    }

    function initializePlayers() {
        if (playersInitialized) {
            return;
        }

        playersInitialized = true;

        loadPlayerJs().then(function (canUsePlayerjs) {
            frames.forEach(function (frame) {
                renderFrame(frame, canUsePlayerjs);
            });
        });
    }

    function maybeInitializePlayers() {
        if (!musicArticle.classList.contains("active")) {
            return;
        }

        initializePlayers();
    }

    new MutationObserver(function () {
        maybeInitializePlayers();
    }).observe(musicArticle, {
        attributes: true,
        attributeFilter: ["class"]
    });

    window.addEventListener("hashchange", function () {
        window.setTimeout(maybeInitializePlayers, 0);
    });

    maybeInitializePlayers();
})();

(function () {
    var artArticle = document.getElementById("art");
    if (!artArticle) {
        return;
    }

    function pauseArtVideos() {
        artArticle.querySelectorAll(".album-art-card video").forEach(function (video) {
            if (!video.paused) {
                video.pause();
            }
        });
    }

    function syncArtMediaState() {
        if (!artArticle.classList.contains("active")) {
            pauseArtVideos();
        }
    }

    new MutationObserver(function () {
        syncArtMediaState();
    }).observe(artArticle, {
        attributes: true,
        attributeFilter: ["class"]
    });

    window.addEventListener("hashchange", function () {
        window.setTimeout(syncArtMediaState, 0);
    });

    syncArtMediaState();
})();

(function () {
    var modal = document.getElementById("music-share-modal");
    if (!modal) {
        return;
    }

    var titleElement = modal.querySelector("#music-share-title");
    var linkInput = modal.querySelector("#music-share-link");
    var copyButton = modal.querySelector("[data-share-copy]");
    var copyLabel = modal.querySelector("[data-share-copy-label]");
    var closeButton = modal.querySelector("[data-share-close]");
    var dialog = modal.querySelector(".music-share-dialog");
    var lastTrigger = null;
    var copyResetTimer = 0;
    var focusableSelector = [
        'a[href]:not([tabindex="-1"])',
        'button:not([disabled]):not([tabindex="-1"])',
        'input:not([disabled]):not([type="hidden"]):not([tabindex="-1"])',
        '[tabindex]:not([tabindex="-1"])'
    ].join(", ");
    var platformLinks = {
        threads: modal.querySelector('[data-share-platform="threads"]'),
        facebook: modal.querySelector('[data-share-platform="facebook"]'),
        x: modal.querySelector('[data-share-platform="x"]'),
        email: modal.querySelector('[data-share-platform="email"]')
    };

    function getFocusableElements() {
        if (!dialog) {
            return [];
        }

        return Array.prototype.filter.call(dialog.querySelectorAll(focusableSelector), function (element) {
            return !element.hidden && element.getAttribute("aria-hidden") !== "true";
        });
    }

    function buildAbsoluteUrl(path) {
        try {
            return new URL(path, window.location.origin).toString();
        } catch (error) {
            return window.location.href;
        }
    }

    function setCopiedState(isCopied) {
        if (!copyButton) {
            return;
        }

        copyButton.classList.toggle("is-copied", isCopied);
        copyButton.setAttribute("aria-label", isCopied ? "Share link copied" : "Copy share link");
        if (copyLabel) {
            copyLabel.textContent = isCopied ? "Copied" : "Copy";
        }
    }

    function openShareModal(trigger) {
        var title = trigger.getAttribute("data-share-title") || "JosephlovesJohn";
        var sharePath = trigger.getAttribute("data-share-path") || window.location.pathname;
        var shareUrl = buildAbsoluteUrl(sharePath);
        var shareText = 'Listen to "' + title + '" by JosephlovesJohn.';

        lastTrigger = trigger;
        titleElement.textContent = title;
        linkInput.value = shareUrl;

        platformLinks.threads.href = "https://www.threads.net/intent/post?text=" + encodeURIComponent(shareText + " " + shareUrl);
        platformLinks.facebook.href = "https://www.facebook.com/sharer/sharer.php?u=" + encodeURIComponent(shareUrl);
        platformLinks.x.href = "https://twitter.com/intent/tweet?text=" + encodeURIComponent(shareText) + "&url=" + encodeURIComponent(shareUrl);
        platformLinks.email.href = "mailto:?subject=" + encodeURIComponent(title + " - JosephlovesJohn") + "&body=" + encodeURIComponent(shareText + "\n\n" + shareUrl);

        setCopiedState(false);
        modal.classList.add("is-visible");
        modal.setAttribute("aria-hidden", "false");
        document.body.classList.add("is-share-modal-visible");

        if (closeButton) {
            closeButton.focus();
        }
    }

    function closeShareModal() {
        modal.classList.remove("is-visible");
        modal.setAttribute("aria-hidden", "true");
        document.body.classList.remove("is-share-modal-visible");

        if (lastTrigger) {
            lastTrigger.focus();
        }
    }

    document.querySelectorAll(".music-share-trigger").forEach(function (trigger) {
        trigger.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            openShareModal(trigger);
        });
    });

    modal.addEventListener("click", function (event) {
        event.stopPropagation();
        if (event.target === modal || event.target.hasAttribute("data-share-close")) {
            closeShareModal();
        }
    });

    if (closeButton) {
        closeButton.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            closeShareModal();
        });
    }

    if (dialog) {
        dialog.addEventListener("click", function (event) {
            event.stopPropagation();
        });
    }

    window.addEventListener("keyup", function (event) {
        if ((event.key === "Escape" || event.keyCode === 27) && modal.classList.contains("is-visible")) {
            event.preventDefault();
            event.stopImmediatePropagation();
            closeShareModal();
        }
    }, true);

    document.addEventListener("keydown", function (event) {
        if (event.key !== "Tab" || !modal.classList.contains("is-visible")) {
            return;
        }

        var focusableElements = getFocusableElements();
        if (!focusableElements.length) {
            return;
        }

        var firstElement = focusableElements[0];
        var lastElement = focusableElements[focusableElements.length - 1];
        if (event.shiftKey && document.activeElement === firstElement) {
            event.preventDefault();
            lastElement.focus();
        } else if (!event.shiftKey && document.activeElement === lastElement) {
            event.preventDefault();
            firstElement.focus();
        }
    });

    if (copyButton && linkInput) {
        copyButton.addEventListener("click", function () {
            var linkValue = linkInput.value;

            function markCopied() {
                clearTimeout(copyResetTimer);
                setCopiedState(true);
                copyResetTimer = window.setTimeout(function () {
                    setCopiedState(false);
                }, 1600);
            }

            function fallbackCopy() {
                linkInput.focus();
                linkInput.select();
                linkInput.setSelectionRange(0, linkValue.length);

                try {
                    if (document.execCommand("copy")) {
                        markCopied();
                    }
                } catch (error) {
                    return;
                }
            }

            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(linkValue).then(markCopied, fallbackCopy);
                return;
            }

            fallbackCopy();
        });
    }
})();

(function () {
    var lightbox = document.getElementById("art-lightbox");
    if (!lightbox) {
        return;
    }

    var lightboxImage = lightbox.querySelector(".art-lightbox-image");
    var lightboxCaption = lightbox.querySelector(".art-lightbox-caption");
    var lightboxInner = lightbox.querySelector(".art-lightbox-inner");
    var lightboxCloseButton = lightbox.querySelector("[data-art-close]");
    var lastTrigger = null;

    function getLightboxFocusableElements() {
        if (!lightboxInner && !lightboxCloseButton) {
            return [];
        }

        return Array.prototype.filter.call(
            lightbox.querySelectorAll('a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'),
            function (element) {
                return !element.hidden && element.getAttribute("aria-hidden") !== "true";
            }
        );
    }

    function closeLightbox() {
        lightbox.classList.remove("is-visible");
        lightbox.setAttribute("aria-hidden", "true");
        document.body.classList.remove("is-lightbox-visible");
        lightboxImage.removeAttribute("src");
        lightboxImage.alt = "";
        lightboxCaption.textContent = "";
        if (lastTrigger) {
            lastTrigger.focus();
        }
    }

    document.querySelectorAll('[data-art-lightbox="image"]').forEach(function (trigger) {
        trigger.addEventListener("click", function (event) {
            event.preventDefault();

            var targetUrl = trigger.getAttribute("href");
            if (!targetUrl) {
                return;
            }

            lastTrigger = trigger;
            var image = trigger.querySelector("img");
            lightboxImage.src = targetUrl;
            lightboxImage.alt = image ? image.alt : "Artwork";
            lightboxCaption.textContent = trigger.getAttribute("data-art-caption") || "";

            lightbox.classList.add("is-visible");
            lightbox.setAttribute("aria-hidden", "false");
            document.body.classList.add("is-lightbox-visible");
            lightbox.scrollTop = 0;
            window.requestAnimationFrame(function () {
                if (lightboxCloseButton) {
                    lightboxCloseButton.focus();
                }
            });
        });
    });

    lightbox.addEventListener("click", function (event) {
        event.stopPropagation();

        if (event.target === lightbox || event.target.hasAttribute("data-art-close")) {
            event.preventDefault();
            closeLightbox();
        }
    });

    if (lightboxInner) {
        lightboxInner.addEventListener("click", function (event) {
            event.stopPropagation();
        });
    }

    window.addEventListener("keyup", function (event) {
        if ((event.key === "Escape" || event.keyCode === 27) && lightbox.classList.contains("is-visible")) {
            event.preventDefault();
            event.stopPropagation();
            closeLightbox();
        }
    }, true);

    document.addEventListener("keydown", function (event) {
        if (event.key !== "Tab" || !lightbox.classList.contains("is-visible")) {
            return;
        }

        var focusableElements = getLightboxFocusableElements();
        if (!focusableElements.length) {
            return;
        }

        var firstElement = focusableElements[0];
        var lastElement = focusableElements[focusableElements.length - 1];
        if (event.shiftKey && document.activeElement === firstElement) {
            event.preventDefault();
            lastElement.focus();
        } else if (!event.shiftKey && document.activeElement === lastElement) {
            event.preventDefault();
            firstElement.focus();
        }
    });

    window.addEventListener("hashchange", function () {
        if (lightbox.classList.contains("is-visible")) {
            closeLightbox();
        }
    });
})();
