/** @odoo-module **/

(function () {
  "use strict";

  function fmt3(n) {
    const x = Number(n || 0);
    return x.toLocaleString(undefined, { minimumFractionDigits: 3, maximumFractionDigits: 3 });
  }

  function parseNum(str) {
    if (!str) return 0;
    return Number(String(str).replace(/,/g, "")) || 0;
  }

  function recalcTotal(tbody, totalSpanIds) {
    let sum = 0;
    tbody.querySelectorAll("tr:not(.d-none) .o-bucket-amt").forEach(td => {
      sum += parseNum(td.textContent);
    });
    for (const id of totalSpanIds) {
      const el = document.getElementById(id);
      if (el) el.textContent = fmt3(sum);
    }
  }
  function bindBucketSearch() {
    const table = document.getElementById("bucketTable");
    if (!table) return;

    const tbody = table.querySelector("tbody");
    const search = document.getElementById("bucketSearch");
    const clear = document.getElementById("bucketClear");

    const doFilter = () => {
      const q = (search.value || "").trim().toLowerCase();
      tbody.querySelectorAll("tr.o-bucket-row").forEach(tr => {
        const hay = tr.dataset.q || tr.textContent.toLowerCase();
        tr.classList.toggle("d-none", !!q && !hay.includes(q));
      });
      recalcTotal(tbody, ["bucketTotal", "bucketTotalFoot"]);
    };

    search.addEventListener("input", doFilter);
    clear.addEventListener("click", () => { search.value = ""; doFilter(); });

    // initial normalize
    recalcTotal(tbody, ["bucketTotal", "bucketTotalFoot"]);
  }

  document.addEventListener("DOMContentLoaded", bindBucketSearch);
})();
