/** @odoo-module **/
document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("recv_refresh");
  const status = document.getElementById("recv_refresh_status");
  if (!btn) return;
  btn.addEventListener("click", () => {
    btn.disabled = true;
    const started = new Date().toLocaleTimeString();
    if (status) status.textContent = `Refreshing… (${started})`;
    const url = new URL(window.location.href);
    url.searchParams.set("ts", Date.now().toString());
    window.location.replace(url.toString());
  });
});
