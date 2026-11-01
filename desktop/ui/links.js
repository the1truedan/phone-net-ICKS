// Open outside (https) links in the normal browser instead of inside the app window.
document.addEventListener("click", ev => {
  const a = ev.target.closest && ev.target.closest("a[href^='https://']");
  const T = window.__TAURI__;
  if (!a || !T || !T.core) return;
  ev.preventDefault();
  T.core.invoke("open_external", { url: a.href }).catch(() => {});
});
