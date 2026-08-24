(function () {
    "use strict";

    document.querySelectorAll("[data-auto-submit]").forEach(function (form) {
        form.querySelectorAll('input[type="checkbox"]').forEach(function (checkbox) {
            checkbox.addEventListener("change", function () {
                form.submit();
            });
        });
    });

    document.querySelectorAll("[data-filters-toggle]").forEach(function (button) {
        var panel = document.getElementById(button.dataset.filtersToggle);
        if (!panel) {
            return;
        }
        button.addEventListener("click", function () {
            var expanded = panel.classList.toggle("is-expanded");
            button.setAttribute("aria-expanded", expanded);
        });
    });
})();
