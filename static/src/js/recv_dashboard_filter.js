/** @odoo-module **/

(function () {
  function num(v) { return Number(v || 0); }

  function matchesBucket(tr, bucket) {
    if (!bucket) return true;
    const c = num(tr.dataset.current);
    const a = num(tr.dataset.d0_30);
    const b = num(tr.dataset.d31_60);
    const d = num(tr.dataset.d61_90);
    const e = num(tr.dataset.d90p);

    if (bucket === 'hasneg') {
      return [c, a, b, d, e].some(x => x < 0);
    }
    if (bucket === 'current') return c !== 0;
    if (bucket === 'd0_30') return a !== 0;
    if (bucket === 'd31_60') return b !== 0;
    if (bucket === 'd61_90') return d !== 0;
    if (bucket === 'd90p')   return e !== 0;
    return true;
  }

  function shouldKeep(tr, q, bucket, zeroPolicy) {
    const name = (tr.dataset.customer_name || '').toLowerCase();
    const total = num(tr.dataset.total);

    if (zeroPolicy === 'hide_zero' && total === 0) return false;
    if (q && q.length >= 2 && !name.includes(q)) return false;
    if (!matchesBucket(tr, bucket)) return false;

    return true;
  }

  function applyFilter() {
    const q       = (document.getElementById('recvSearch')?.value || '').trim().toLowerCase();
    const bucket  = document.getElementById('recvBucket')?.value || '';
    const zeroPol = document.getElementById('recvZero')?.value || 'hide_zero';

    const rows = document.querySelectorAll('#recv_table tbody tr.o-recv-row');
    let shown = 0;

    rows.forEach((tr) => {
      const keep = shouldKeep(tr, q, bucket, zeroPol);
      tr.style.display = keep ? '' : 'none';

      // hide/show expander partner row too
      const exp = tr.nextElementSibling;
      if (exp && exp.classList.contains('o-recv-expand')) {
        if (!keep) exp.style.display = 'none';
        else if (!exp.classList.contains('open')) exp.style.display = 'none';
      }
      if (keep) shown += 1;
    });

    // (optional) could show a small “n results” chip
    // console.log('visible rows:', shown);
  }

  function bindToolbar() {
    const s = document.getElementById('recvSearch');
    const b = document.getElementById('recvBucket');
    const z = document.getElementById('recvZero');
    const c = document.getElementById('recvClear');

    if (s) s.addEventListener('input', applyFilter);
    if (b) b.addEventListener('change', applyFilter);
    if (z) z.addEventListener('change', applyFilter);
    if (c) c.addEventListener('click', () => {
      if (s) s.value = '';
      if (b) b.value = '';
      if (z) z.value = 'hide_zero';
      applyFilter();
      s?.focus();
    });

    applyFilter(); // initial
  }

  document.addEventListener('DOMContentLoaded', bindToolbar);
})();
