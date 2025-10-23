/** @odoo-module **/

// ---------- small helpers ----------
const fmt = (n) => Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: 2 });

function groupByBucket(rows) {
  const b = { current: [], d0_30: [], d31_60: [], d61_90: [], d90p: [] };
  (rows || []).forEach(r => {
    const key = (r.bucket || "current").toLowerCase();
    (b[key] || b.current).push(r);
  });
  return b;
}

function postJson(url, payload) {
  return fetch(url, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {}),
  }).then(r => r.json());
}

// ---------- renderer ----------
function renderInvoices(rows) {
  if (!rows || !rows.length) {
    return "<div class='o-recv-expand__empty'>No invoices found.</div>";
  }

  // normalize field names coming from the API (defensive)
  const norm = rows.map(r => ({
    DATE: r.DATEINVC || r.date || "",
    IDORDERNBR: r.IDORDERNBR || r.order || "",
    IDCUSTPO: r.IDCUSTPO || r.customer_po || "",
    DESCINVC: r.DESCINVC || r.description || "",
    AMT: Number(r.AMTINVCHC ?? r.amount ?? 0),
    BUCKET: (r.bucket || "current").toLowerCase(),
  }));

  const by = groupByBucket(norm);
  const sectionsOrder = [
    ["current", "Current"],
    ["d0_30", "1–30"],
    ["d31_60", "31–60"],
    ["d61_90", "61–90"],
    ["d90p",   "90+"],
  ];

  const sectionsHtml = sectionsOrder.map(([key, label]) => {
    const items = by[key];
    if (!items || !items.length) return "";

    const total = items.reduce((s, r) => s + (r.AMT || 0), 0);

    const rowsHtml = items.map(r => `
      <tr>
        <td>${r.DATE || ""}</td>
        <td>${r.IDORDERNBR || ""}</td>
        <td>${r.IDCUSTPO || ""}</td>
        <td>${r.DESCINVC || ""}</td>
        <td class="num">${fmt(r.AMT)}</td>
      </tr>
    `).join("");

    // section block
    return `
      <div class="o-recv-expand__section">
        <div class="o-recv-expand__sectionHeader">
          <span class="badge badge-${key}">${label}</span>
          <span class="o-recv-expand__sectionTotal">Total: ${fmt(total)}</span>
        </div>
        <table class="o-recv-expand__table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Order #</th>
              <th>Customer PO</th>
              <th>Description</th>
              <th class="num">Amount</th>
            </tr>
          </thead>
          <tbody>
            ${rowsHtml}
          </tbody>
        </table>
      </div>
    `;
  }).join("");

  return sectionsHtml || "<div class='o-recv-expand__empty'>No invoices found.</div>";
}

// ---------- behavior (expand/collapse + fetch) ----------
function setupExpandableRows() {
  const tbl = document.getElementById("recv_table");
  if (!tbl) return;

  tbl.addEventListener("click", async (ev) => {
    const row = ev.target.closest("tr.o-recv-row");
    if (!row) return;

    const expander = row.nextElementSibling;
    if (!expander || !expander.classList.contains("o-recv-expand")) return;

    // toggle if already loaded
    if (expander.dataset.loaded === "1") {
      expander.classList.toggle("open");
      return;
    }

    // first time: fetch
    const code = row.dataset.customer_code || null;
    const name = row.dataset.customer_name || null;

    const body = expander.querySelector(".o-recv-expand__body");
    body.innerHTML = "<div class='o-recv-expand__loading'>Loading…</div>";

    try {
      // support both {"params":{...}} and flat payload; we send flat
      const res = await postJson("/recv/invoices", { customer_code: code, customer_name: name });
      const rows = (res && res.result ? res.result.rows : res.rows) || [];
      body.innerHTML = renderInvoices(rows);
      expander.dataset.loaded = "1";
      expander.classList.add("open");
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error(e);
      body.innerHTML = "<div class='o-recv-expand__error'>Failed to load invoices.</div>";
    }
  });
}

document.addEventListener("DOMContentLoaded", setupExpandableRows);
