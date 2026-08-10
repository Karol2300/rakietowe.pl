(function () {
    "use strict";

    var dataEl = document.getElementById("variants-data");
    if (!dataEl) return;

    var variants = JSON.parse(dataEl.textContent);
    var variantsById = {};
    variants.forEach(function (v) {
        variantsById[v.id] = v;
    });

    var priceCurrent = document.getElementById("price-current");
    var stockDisplay = document.getElementById("stock-display");
    var addToCartButton = document.getElementById("add-to-cart-button");
    var notifyForm = document.getElementById("notify-form");
    var notifyFormAction = document.getElementById("notify-me-form");
    var radios = document.querySelectorAll('input[name="variant"]');

    function applyVariant(variant) {
        if (!variant) return;
        var inStock = variant.stock > 0;
        if (priceCurrent) {
            priceCurrent.textContent = variant.price + " zł";
        }
        if (stockDisplay) {
            var label = inStock ? stockDisplay.dataset.inStockLabel : stockDisplay.dataset.outOfStockLabel;
            stockDisplay.innerHTML = "";
            var span = document.createElement("span");
            span.className = inStock ? "product-info__stock--in" : "product-info__stock--out";
            span.textContent = label;
            stockDisplay.appendChild(span);
        }
        if (addToCartButton) {
            addToCartButton.disabled = !inStock;
        }
        if (notifyForm) {
            notifyForm.hidden = inStock;
            if (!inStock && notifyFormAction) {
                var template = notifyForm.getAttribute("data-notify-url-template");
                notifyFormAction.setAttribute("action", template.replace("/0/", "/" + variant.id + "/"));
            }
        }
    }

    radios.forEach(function (radio) {
        radio.addEventListener("change", function () {
            applyVariant(variantsById[radio.value]);
        });
    });

    var checked = document.querySelector('input[name="variant"]:checked');
    if (checked) {
        applyVariant(variantsById[checked.value]);
    }
})();
