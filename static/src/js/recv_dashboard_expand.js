/** @odoo-module **/

// ----- helpers --------------------------------------------------------------
function fmtMoney(n) {
  return Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: 2 });
}

// static/src/js/recv_dashboard_expand.js
function postJson(url, payload) {
  // Odoo expects {"params": {...}} in JSON-RPC format
  const body = JSON.stringify({ params: payload || {} });
  console.debug("[recv] POST", url, payload);  // for debugging

  return fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body,
  }).then((r) => r.json());
}


// Build the mini-table with ONLY the requested columns.
function renderInvoices(rows) {
  if (!rows || !rows.length) {
    return "<div class='o-recv-expand__empty'>No invoices found.</div>";
  }

  const total = rows.reduce((s, r) => s + Number(r.AMTINVCHC || 0), 0);

  const trs = rows.map((r) => `
    <tr>
      <td>${r.DATEINVC || ""}</td>
      <td>${r.IDORDERNBR || ""}</td>
      <td>${r.IDCUSTPO || ""}</td>
      <td>${r.DESCINVC || ""}</td>
      <td class="num">${fmtMoney(r.AMTINVCHC)}</td>
    </tr>
  `).join("");

  return `
    <div class="o-recv-expand__section">
      <div class="o-recv-expand__sectionHeader">
        <span>Invoices</span>
        <span class="o-recv-expand__sectionTotal">Total: ${fmtMoney(total)}</span>
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
        <tbody>${trs}</tbody>
      </table>
    </div>
  `;
}

// ----- main -----------------------------------------------------------------
// static/src/js/recv_dashboard_expand.js
function setupExpandableRows() {
  const tbl = document.getElementById("recv_table");
  if (!tbl) return;

  tbl.addEventListener("click", async (ev) => {
    const row = ev.target.closest("tr.o-recv-row");
    if (!row) return;

    const expandRow = row.nextElementSibling;
    if (!expandRow || !expandRow.classList.contains("o-recv-expand")) return;

    if (expandRow.dataset.loaded === "1") {
      expandRow.classList.toggle("open");
      return;
    }

    const code = (row.dataset.customer_code || "").trim();
    const name = (row.dataset.customer_name || "").trim();

    const body = expandRow.querySelector(".o-recv-expand__body");
    body.innerHTML = "<div class='o-recv-expand__loading'>Loading…</div>";

    try {
      const res = await postJson("/recv/invoices", {
        customer_code: code,
        customer_name: name,
      });
      // handle both {"rows": []} and {"result": {"rows": []}}
      body.innerHTML = renderInvoices(
        (res && res.result && res.result.rows) || res.rows || []
      );
      expandRow.dataset.loaded = "1";
      expandRow.classList.add("open");
    } catch (e) {
      body.innerHTML = "<div class='o-recv-expand__error'>Failed to load invoices.</div>";
      console.error(e);
    }
  });
}

document.addEventListener("DOMContentLoaded", setupExpandableRows);
