(function () {
    var modal = document.getElementById("music-cart-modal");
    var floatingButton = document.getElementById("floating-cart-button");
    var siteUtils = window.siteUtils || {};
    var getCookie = siteUtils.getCookie;

    if (!modal || !floatingButton) {
        return;
    }

    var dialog = modal.querySelector(".music-cart-dialog");
    var closeButtons = modal.querySelectorAll("[data-cart-close]");
    var checkoutButton = modal.querySelector("[data-cart-checkout]");
    var subtotalValue = modal.querySelector("[data-cart-subtotal]");
    var itemList = modal.querySelector("[data-cart-items]");
    var emptyState = modal.querySelector("[data-cart-empty]");
    var countTargets = document.querySelectorAll("[data-cart-count]");
    var buyButtons = document.querySelectorAll("[data-cart-add-url]");
    var musicUrl = modal.getAttribute("data-music-url") || "/music/";
    var lastTrigger = null;
    var focusableSelector = [
        'a[href]:not([tabindex="-1"])',
        'button:not([disabled]):not([tabindex="-1"])',
        'input:not([disabled]):not([type="hidden"]):not([tabindex="-1"])',
        'select:not([disabled]):not([tabindex="-1"])',
        'textarea:not([disabled]):not([tabindex="-1"])',
        '[tabindex]:not([tabindex="-1"])'
    ].join(", ");

    function getFocusableElements() {
        if (!dialog) {
            return [];
        }

        return Array.prototype.filter.call(dialog.querySelectorAll(focusableSelector), function (element) {
            return !element.hidden && element.getAttribute("aria-hidden") !== "true";
        });
    }

    function trackAddToCart(button) {
        if (!button || !window.siteAnalytics || typeof window.siteAnalytics.track !== "function") {
            return;
        }

        window.siteAnalytics.track("Add to Cart", {
            props: {
                slug: button.getAttribute("data-cart-item-slug") || "",
                title: button.getAttribute("data-cart-item-title") || "",
                price_gbp: button.getAttribute("data-cart-item-price") || ""
            }
        });
    }

    function getCsrfToken() {
        var cookieToken = getCookie("csrftoken");
        if (cookieToken) {
            return cookieToken;
        }

        var hiddenToken = document.querySelector("#site-csrf-token input[name='csrfmiddlewaretoken']");
        return hiddenToken ? hiddenToken.value : "";
    }

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function renderCartItems(items) {
        if (!itemList) {
            return;
        }

        itemList.innerHTML = items
            .map(function (item) {
                return [
                    '<li class="music-cart-item" data-cart-slug="' + escapeHtml(item.slug) + '">',
                    '<img src="' + escapeHtml(item.art_url) + '" alt="' + escapeHtml(item.art_alt || item.title) + '">',
                    '<div class="music-cart-item-copy">',
                    '<strong>' + escapeHtml(item.title) + '</strong>',
                    '<span>' + escapeHtml(item.meta || item.artist_name) + '</span>',
                    '</div>',
                    '<span class="music-cart-item-price">' + escapeHtml(item.price_display) + '</span>',
                    '<button type="button" class="music-cart-remove" data-cart-remove-url="' + escapeHtml(item.remove_url) + '" aria-label="Remove ' + escapeHtml(item.title) + ' from cart">Remove</button>',
                    '</li>'
                ].join("");
            })
            .join("");
    }

    function applySummary(summary) {
        renderCartItems(summary.items || []);
        if (subtotalValue) {
            subtotalValue.textContent = summary.subtotal_display || "£0.00";
        }

        countTargets.forEach(function (target) {
            target.textContent = String(summary.item_count || 0);
        });

        floatingButton.classList.toggle("is-hidden", !!summary.is_empty);
        modal.classList.toggle("has-items", !summary.is_empty);

        if (emptyState) {
            emptyState.classList.toggle("is-hidden", !summary.is_empty);
        }

        if (checkoutButton) {
            checkoutButton.setAttribute("href", summary.checkout_url || checkoutButton.getAttribute("href") || "#");
            checkoutButton.classList.toggle("is-disabled", !!summary.is_empty);
            checkoutButton.setAttribute("aria-disabled", summary.is_empty ? "true" : "false");
        }
    }

    function openModal(trigger) {
        lastTrigger = trigger || floatingButton;
        modal.classList.add("is-visible");
        modal.setAttribute("aria-hidden", "false");
        document.body.classList.add("is-cart-modal-visible");
        window.requestAnimationFrame(function () {
            var focusableElements = getFocusableElements();
            if (focusableElements.length) {
                focusableElements[0].focus();
            }
        });
    }

    function closeModal() {
        modal.classList.remove("is-visible");
        modal.setAttribute("aria-hidden", "true");
        document.body.classList.remove("is-cart-modal-visible");
        if (lastTrigger) {
            lastTrigger.focus();
        }
    }

    function returnToMusicView() {
        if (window.location.pathname !== musicUrl) {
            window.location.href = musicUrl;
            return;
        }

        if (window.location.hash !== "#music") {
            window.location.hash = "music";
        }
    }

    function postJson(url) {
        return fetch(url, {
            method: "POST",
            headers: {
                "X-CSRFToken": getCsrfToken(),
                "X-Requested-With": "XMLHttpRequest"
            },
            credentials: "same-origin"
        }).then(function (response) {
            if (!response.ok) {
                throw new Error("Cart request failed");
            }
            return response.json();
        });
    }

    floatingButton.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        openModal(floatingButton);
    });

    closeButtons.forEach(function (button) {
        button.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            closeModal();
        });
    });

    modal.addEventListener("click", function (event) {
        event.stopPropagation();
        if (event.target === modal || event.target.hasAttribute("data-cart-close")) {
            closeModal();
            returnToMusicView();
        }
    });

    if (dialog) {
        dialog.addEventListener("click", function (event) {
            event.stopPropagation();
        });
    }

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && modal.classList.contains("is-visible")) {
            closeModal();
            return;
        }

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

    dialog.addEventListener("click", function (event) {
        var removeButton = event.target.closest("[data-cart-remove-url]");
        if (!removeButton) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();
        postJson(removeButton.getAttribute("data-cart-remove-url"))
            .then(function (summary) {
                applySummary(summary);
                if (summary.is_empty) {
                    closeModal();
                }
            })
            .catch(function () {
                window.alert("Something went wrong removing that song. Please try again.");
            });
    });

    buyButtons.forEach(function (button) {
        button.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            var url = button.getAttribute("data-cart-add-url");
            if (!url) {
                return;
            }

            button.disabled = true;
            postJson(url)
                .then(function (summary) {
                    applySummary(summary);
                    trackAddToCart(button);
                    openModal(button);
                })
                .catch(function () {
                    window.alert("Something went wrong adding that song. Please try again.");
                })
                .finally(function () {
                    button.disabled = false;
                });
        });
    });
})();
