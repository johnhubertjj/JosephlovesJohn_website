(function () {
    var modal = document.getElementById("music-cart-modal");
    var floatingButton = document.getElementById("floating-cart-button");

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
    var lastTrigger = null;

    function getCookie(name) {
        var value = "; " + document.cookie;
        var parts = value.split("; " + name + "=");
        if (parts.length === 2) {
            return parts.pop().split(";").shift();
        }
        return "";
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
    }

    function closeModal() {
        modal.classList.remove("is-visible");
        modal.setAttribute("aria-hidden", "true");
        document.body.classList.remove("is-cart-modal-visible");
        if (lastTrigger) {
            lastTrigger.focus();
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

    floatingButton.addEventListener("click", function () {
        openModal(floatingButton);
    });

    closeButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            closeModal();
        });
    });

    modal.addEventListener("click", function (event) {
        if (event.target === modal || event.target.hasAttribute("data-cart-close")) {
            closeModal();
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && modal.classList.contains("is-visible")) {
            closeModal();
        }
    });

    modal.addEventListener("click", function (event) {
        var removeButton = event.target.closest("[data-cart-remove-url]");
        if (!removeButton) {
            return;
        }

        event.preventDefault();
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
        button.addEventListener("click", function () {
            var url = button.getAttribute("data-cart-add-url");
            if (!url) {
                return;
            }

            button.disabled = true;
            postJson(url)
                .then(function (summary) {
                    applySummary(summary);
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
