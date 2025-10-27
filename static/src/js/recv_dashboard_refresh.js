/** @odoo-module **/

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', () => {
    setupRefreshButton();
    setupZeroTotalToggle();  // default = SHOW
  });

  // ---------------------------
  // Refresh button (unchanged)
  // ---------------------------
  function setupRefreshButton() {
    const btn = document.getElementById('recv_refresh');
    const status = document.getElementById('recv_refresh_status');
    if (!btn) return;

    btn.addEventListener('click', () => {
      btn.disabled = true;
      const started = new Date().toLocaleTimeString();
      if (status) status.textContent = `Refreshing… (${started})`;
      const url = new URL(window.location.href);
      url.searchParams.set('ts', Date.now().toString());
      window.location.replace(url.toString());
    });
  }

  // ---------------------------------------------------
  // Hide/Show zero-total rows (default = SHOW)
  // ---------------------------------------------------
  function setupZeroTotalToggle() {
    const sel = document.getElementById('recv_zero_toggle');
    // If the control isn’t on this page, nothing to do
    if (!sel) return;

    // Default to SHOW if there is no saved preference
    const saved = localStorage.getItem('recv_hide_zero'); // 'hide' | 'show' | null
    const startValue = saved === 'hide' ? 'hide' : 'show';
    sel.value = startValue;

    // Apply once on load
    applyHideZero(startValue === 'hide');

    // Save preference and re-apply when changed
    sel.addEventListener('change', () => {
      const hide = sel.value === 'hide';
      localStorage.setItem('recv_hide_zero', hide ? 'hide' : 'show');
      applyHideZero(hide);
    });
  }

  // Hide rows with total==0.000; show otherwise.
  // Also hide matching expander row.
  function applyHideZero(hide) {
    const rows = document.querySelectorAll('#recv_table tbody tr.o-recv-row');
    rows.forEach((tr) => {
      const total = readRowTotal(tr);
      const shouldHide = hide && Math.abs(total) < 1e-9;
      tr.style.display = shouldHide ? 'none' : '';

      // Hide the expander row just below, if present
      const expander = tr.nextElementSibling;
      if (expander && expander.classList.contains('o-recv-expand')) {
        expander.style.display = shouldHide ? 'none' : (expander.classList.contains('open') ? 'table-row' : 'none');
      }
    });
  }

  // Prefer data-total, else parse the last numeric cell.
  function readRowTotal(tr) {
    if (tr.dataset && tr.dataset.total != null) {
      return Number(tr.dataset.total || 0);
    }
    // Fallback: read last cell’s text
    const last = tr.querySelector('td:last-child');
    if (!last) return 0;
    // Remove commas and spaces, then Number()
    const raw = (last.textContent || '').replace(/[, ]/g, '');
    const v = Number(raw);
    return isNaN(v) ? 0 : v;
  }
})();
