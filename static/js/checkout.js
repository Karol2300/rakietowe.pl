(function () {
    "use strict";

    var container = document.querySelector("[data-locker-method-id]");
    var lockerField = document.querySelector("[data-locker-field]");
    if (!container || !lockerField) return;

    var lockerMethodId = container.getAttribute("data-locker-method-id");
    var radios = container.querySelectorAll('input[name="shipping_method"]');

    function sync() {
        var checked = container.querySelector('input[name="shipping_method"]:checked');
        lockerField.hidden = !checked || checked.value !== lockerMethodId;
    }

    radios.forEach(function (radio) {
        radio.addEventListener("change", sync);
    });
    sync();
})();
