(function () {
    "use strict";

    function bindRow(row) {
        var removeBtn = row.querySelector(".specs-widget__remove");
        if (removeBtn) {
            removeBtn.addEventListener("click", function () {
                row.remove();
            });
        }
    }

    function init() {
        document.querySelectorAll("[data-specs-widget]").forEach(function (widget) {
            var rowsBody = widget.querySelector("[data-specs-rows]");
            var template = widget.querySelector("[data-specs-row-template]");
            var addButton = widget.querySelector(".specs-widget__add");

            rowsBody.querySelectorAll(".specs-widget__row").forEach(bindRow);

            addButton.addEventListener("click", function () {
                var clone = template.content.cloneNode(true);
                rowsBody.appendChild(clone);
                bindRow(rowsBody.lastElementChild);
            });
        });
    }

    // Django admin includes widget Media <script> tags without `defer`, and
    // typically in <head> - this can run before the widget's own markup
    // (rendered inline with the form field further down the page) exists.
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
