(function () {
    "use strict";

    document.querySelectorAll("[data-auto-submit]").forEach(function (form) {
        form.querySelectorAll('input[type="checkbox"]').forEach(function (checkbox) {
            checkbox.addEventListener("change", function () {
                form.submit();
            });
        });
    });
})();
