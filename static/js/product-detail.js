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
    var radios = document.querySelectorAll('input[name="variant"]');

    function applyVariant(variant) {
        if (!variant) return;
        if (priceCurrent) {
            priceCurrent.textContent = variant.price + " zł";
        }
        if (stockDisplay) {
            var inStock = variant.stock > 0;
            var label = inStock ? stockDisplay.dataset.inStockLabel : stockDisplay.dataset.outOfStockLabel;
            stockDisplay.innerHTML = "";
            var span = document.createElement("span");
            span.className = inStock ? "product-info__stock--in" : "product-info__stock--out";
            span.textContent = label;
            stockDisplay.appendChild(span);
        }
        if (addToCartButton) {
            addToCartButton.disabled = variant.stock <= 0;
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
