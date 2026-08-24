(function () {
    "use strict";

    var COOKIE_NAME = "cookie_consent";

    function hasConsentCookie() {
        return document.cookie.split("; ").some(function (row) {
            return row.indexOf(COOKIE_NAME + "=") === 0;
        });
    }

    var banner = document.getElementById("cookie-banner");
    if (!banner) {
        return;
    }

    if (!hasConsentCookie()) {
        banner.hidden = false;
    }

    var acceptButton = document.getElementById("cookie-banner-accept");
    if (acceptButton) {
        acceptButton.addEventListener("click", function () {
            var oneYear = 60 * 60 * 24 * 365;
            document.cookie = COOKIE_NAME + "=1; max-age=" + oneYear + "; path=/; SameSite=Lax";
            banner.hidden = true;
        });
    }
})();
