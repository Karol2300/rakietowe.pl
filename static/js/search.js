(function () {
    "use strict";

    var form = document.querySelector("[data-search-form]");
    if (!form) return;

    var input = form.querySelector("[data-search-input]");
    var box = form.querySelector("[data-search-suggestions]");
    var suggestionsUrl = form.getAttribute("data-suggestions-url");
    var debounceTimer = null;
    var activeIndex = -1;

    function hideSuggestions() {
        box.hidden = true;
        box.innerHTML = "";
        activeIndex = -1;
    }

    function renderSuggestions(results) {
        box.innerHTML = "";
        if (!results.length) {
            hideSuggestions();
            return;
        }
        results.forEach(function (item) {
            var link = document.createElement("a");
            link.href = item.search_url;
            link.className = "search-suggestions__item";
            var alreadyHasBrand = item.brand && item.name.toLowerCase().indexOf(item.brand.toLowerCase()) === 0;
            link.textContent = item.brand && !alreadyHasBrand ? item.brand + " " + item.name : item.name;
            box.appendChild(link);
        });
        box.hidden = false;
    }

    input.addEventListener("input", function () {
        var query = input.value.trim();
        clearTimeout(debounceTimer);
        if (query.length < 2) {
            hideSuggestions();
            return;
        }
        debounceTimer = setTimeout(function () {
            fetch(suggestionsUrl + "?q=" + encodeURIComponent(query))
                .then(function (response) {
                    return response.ok ? response.json() : { results: [] };
                })
                .then(function (data) {
                    renderSuggestions(data.results || []);
                })
                .catch(function () {
                    hideSuggestions();
                });
        }, 200);
    });

    document.addEventListener("click", function (event) {
        if (!form.contains(event.target)) {
            hideSuggestions();
        }
    });

    input.addEventListener("keydown", function (event) {
        var items = box.querySelectorAll(".search-suggestions__item");
        if (!items.length) return;
        if (event.key === "ArrowDown") {
            event.preventDefault();
            activeIndex = Math.min(activeIndex + 1, items.length - 1);
        } else if (event.key === "ArrowUp") {
            event.preventDefault();
            activeIndex = Math.max(activeIndex - 1, 0);
        } else if (event.key === "Escape") {
            hideSuggestions();
            return;
        } else {
            return;
        }
        items.forEach(function (el, i) {
            el.classList.toggle("is-active", i === activeIndex);
        });
        items[activeIndex].scrollIntoView({ block: "nearest" });
    });
})();
