/** @odoo-module **/

function fmt(n) {
  return Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function groupByBucket(rows) {
  const buckets = { current: [], d0_30: [], d31_60: [], d61_90: [], d90p: [] };
  (rows || []).forEach((r) => {
    const b = (r.bucket || "current").toLowerCase();
    if (buckets[b]) buckets[b].push(r);
    else buckets.current.push(r);
  });
  return buckets;
}

function renderInvoices(rows) {
  if (!rows.length) {
    return "<div class='o-recv-expand__empty'>No invoices found.</div>";
  }
  const by = groupByBucket(rows);
  const order = [
    ["current","Current"],
    ["d0_30","1–30"],
    ["d31_60","31–60"],
    ["d61_90","61–90"],
    ["d90p","90+"],
  ];

  const sections = order.map(([key, label]) => {
    const items = by[key];
    if (!items.length) return "";
    const total = items.reduce((s, r) => s + Number(r.amount || 0), 0);
    const rowsHtml = items.map((r) => `
      <tr>
        <td>${r.number || ""}</td>
        <td>${r.date || ""}</td>
        <td>${r.due_date || ""}</td>
        <td class="num">${r.days_overdue}</td>
        <td class="num">${fmt(r.amount)}</td>
      </tr>
    `).join("");

    return `
      <div class="o-recv-expand__section">
        <div class="o-recv-expand__sectionHeader">
          <span class="badge badge-${key}">${label}</span>
          <span class="o-recv-expand__sectionTotal">Total: ${fmt(total)}</span>
        </div>
        <table class="o-recv-expand__table">
          <thead>
            <tr>
              <th>Invoice</th>
              <th>Date</th>
              <th>Due</th>
              <th class="num">Days</th>
              <th class="num">Amount</th>
            </tr>
          </thead>
          <tbody>${rowsHtml}</tbody>
        </table>
      </div>
    `;
  }).join("");

  return sections || "<div class='o-recv-expand__empty'>No invoices found.</div>";
}

function postJson(url, payload) {
  return fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {}),
    credentials: "same-origin",
  }).then((r) => r.json());
}

function setupExpandableRows() {
  const tbl = document.getElementById("recv_table");
  if (!tbl) return;

  tbl.addEventListener("click", async (ev) => {
    const row = ev.target.closest("tr.o-recv-row");
    if (!row) return;

    const expandRow = row.nextElementSibling;
    if (!expandRow || !expandRow.classList.contains("o-recv-expand")) return;

    // Toggle open/close if already loaded
    if (expandRow.dataset.loaded === "1") {
      expandRow.classList.toggle("open");
      return;
    }

    // First time: fetch and render
    const code = row.dataset.customer_code || null;
    const name = row.dataset.customer_name || null;
    const body = expandRow.querySelector(".o-recv-expand__body");
    body.innerHTML = "<div class='o-recv-expand__loading'>Loading…</div>";

    try {
      const res = await postJson("/recv/invoices", { customer_code: code, customer_name: name });
      body.innerHTML = renderInvoices(res.rows || []);
      expandRow.dataset.loaded = "1";
      expandRow.classList.add("open");
    } catch (e) {
      body.innerHTML = "<div class='o-recv-expand__error'>Failed to load invoices.</div>";
      // eslint-disable-next-line no-console
      console.error(e);
    }
  });
}

document.addEventListener("DOMContentLoaded", setupExpandableRows);
