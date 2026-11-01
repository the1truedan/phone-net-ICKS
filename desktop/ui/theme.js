// Apply the saved theme before the page draws (no flash). Themes use colors and system fonts only.
(function () {
  var t = "default";
  try { t = localStorage.getItem("theme") || "default"; } catch (e) {}
  document.documentElement.setAttribute("data-theme", t);
  window.setTheme = function (v) {
    document.documentElement.setAttribute("data-theme", v);
    try { localStorage.setItem("theme", v); } catch (e) {}
  };
})();
