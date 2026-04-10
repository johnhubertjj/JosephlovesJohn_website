(function () {
    var frames = document.querySelectorAll(".music-player-frame");
    var canUsePlayerjs = typeof Playerjs !== "undefined";

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

    frames.forEach(function (frame) {
        var file = pickPreferredAudioFile(frame);
        if (!file) {
            return;
        }

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
    });
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
    var platformLinks = {
        threads: modal.querySelector('[data-share-platform="threads"]'),
        facebook: modal.querySelector('[data-share-platform="facebook"]'),
        x: modal.querySelector('[data-share-platform="x"]'),
        email: modal.querySelector('[data-share-platform="email"]')
    };

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

    function closeLightbox() {
        lightbox.classList.remove("is-visible");
        lightbox.setAttribute("aria-hidden", "true");
        document.body.classList.remove("is-lightbox-visible");
        lightboxImage.removeAttribute("src");
        lightboxImage.alt = "";
        lightboxCaption.textContent = "";
    }

    document.querySelectorAll('[data-art-lightbox="image"]').forEach(function (trigger) {
        trigger.addEventListener("click", function (event) {
            event.preventDefault();

            var targetUrl = trigger.getAttribute("href");
            if (!targetUrl) {
                return;
            }

            var image = trigger.querySelector("img");
            lightboxImage.src = targetUrl;
            lightboxImage.alt = image ? image.alt : "Artwork";
            lightboxCaption.textContent = trigger.getAttribute("data-art-caption") || "";

            lightbox.classList.add("is-visible");
            lightbox.setAttribute("aria-hidden", "false");
            document.body.classList.add("is-lightbox-visible");
            lightbox.scrollTop = 0;
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

    window.addEventListener("hashchange", function () {
        if (lightbox.classList.contains("is-visible")) {
            closeLightbox();
        }
    });
})();
