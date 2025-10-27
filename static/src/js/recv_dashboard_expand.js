/** @odoo-module **/

(function () {
  'use strict';

  // --- helpers ---------------------------------------------------------------
  const fmt3 = (n) =>
    Number(n || 0).toLocaleString(undefined, {
      minimumFractionDigits: 3,
      maximumFractionDigits: 3,
    });

  const fmtBlank = (n) => {
    const v = Number(n || 0);
    return Math.abs(v) < 0.0005 ? "" : fmt3(v);
  };

  const escapeHtml = (s) =>
    (s || "").replace(/[&<>"']/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));

  function postJson(url, payload) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(payload || {}),
    }).then((r) => r.json());
  }

  // --- renderer ---------------------------------------------------------------
  function renderInvoiceGridAligned(rows) {
    const list = rows || [];
    if (!list.length) {
      return "<div class='o-recv-expand__empty'>No invoices found.</div>";
    }

    // bucket totals
    const totals = { current: 0, d0_30: 0, d31_60: 0, d61_90: 0, d90p: 0, grand: 0 };

    const trs = list
      .map((r) => {
        const b = (r.bucket || "").toLowerCase();
        const amt = Number(r.AMTINVCHC || 0);
        if (b in totals) totals[b] += amt;
        totals.grand += amt;

        const cells = { current: "", d0_30: "", d31_60: "", d61_90: "", d90p: "" };
        if (b in cells) cells[b] = fmtBlank(amt);

        return `
          <tr>
            <td>
              <div class="o-recv-invwrap">
                <div class="o-recv-grid3">
                  <div class="inv">${escapeHtml(r.IDINV || "")}</div>
                  <div class="date">${escapeHtml(r.DATEINVC || "")}</div>
                  <div class="desc">${escapeHtml(r.DESCINVC || "")}</div>
                </div>
              </div>
            </td>
            <td class="num">${cells.current}</td>
            <td class="num">${cells.d0_30}</td>
            <td class="num">${cells.d31_60}</td>
            <td class="num">${cells.d61_90}</td>
            <td class="num">${cells.d90p}</td>
            <td class="num">${fmtBlank(amt)}</td>
          </tr>
        `;
      })
      .join("");

    const trow = `
      <tr class="o-recv-total">
        <td></td>
        <td class="num">${fmtBlank(totals.current)}</td>
        <td class="num">${fmtBlank(totals.d0_30)}</td>
        <td class="num">${fmtBlank(totals.d31_60)}</td>
        <td class="num">${fmtBlank(totals.d61_90)}</td>
        <td class="num">${fmtBlank(totals.d90p)}</td>
        <td class="num">${fmtBlank(totals.grand)}</td>
      </tr>
    `;

    return `
      <table class="o-recv-align">
        <colgroup>
          <col class="o-recv-col--name" />
          <col class="o-recv-col--amt" />
          <col class="o-recv-col--amt" />
          <col class="o-recv-col--amt" />
          <col class="o-recv-col--amt" />
          <col class="o-recv-col--amt" />
          <col class="o-recv-col--amt" />
        </colgroup>
        <thead>
          <tr>
            <th>
              <div class="o-recv-invwrap">
                <div class="o-recv-grid3">
                  <div class="inv"><strong>Invoice #</strong></div>
                  <div class="date"><strong>Date</strong></div>
                  <div class="desc"><strong>Description</strong></div>
                </div>
              </div>
            </th>
            <th></th><th></th><th></th><th></th><th></th><th></th>
          </tr>
        </thead>
        <tbody>${trs}</tbody>
        <tfoot>${trow}</tfoot>
      </table>
    `;
  }

  // --- handlers ---------------------------------------------------------------
  function bindExpand() {
    const table = document.getElementById("recv_table");
    if (!table) return;

    table.addEventListener("click", async (ev) => {
      const row = ev.target.closest("tr.o-recv-row");
      if (!row) return;

      const expandRow = row.nextElementSibling;
      if (!expandRow || !expandRow.classList.contains("o-recv-expand")) return;

      const body = expandRow.querySelector(".o-recv-expand__body");
      if (!body) return;

      const code = row.dataset.customer_code || null;
      const name = row.dataset.customer_name || null;
      const bucket = (window.__recvBucket || "").toLowerCase();

      if (expandRow.dataset.loaded === "1" && expandRow.dataset.bucket === bucket) {
        expandRow.classList.toggle("open");
        return;
      }

      body.innerHTML = "<div class='o-recv-expand__loading'>Loading…</div>";

      try {
        const res = await postJson("/recv/invoices", { customer_code: code, customer_name: name, bucket });
        const rows = res.result?.rows || res.rows || [];
        body.innerHTML = renderInvoiceGridAligned(rows);
        expandRow.dataset.loaded = "1";
        expandRow.dataset.bucket = bucket;
        expandRow.classList.add("open");
      } catch (e) {
        console.error("[mssql_bridge] invoices fetch failed", e);
        body.innerHTML = "<div class='o-recv-expand__error'>Failed to load invoices.</div>";
      }
    });
  }

  function bindCards() {
    document.querySelectorAll(".o_example_cards .o_card[data-bucket]").forEach((el) => {
      el.addEventListener("click", () => {
        window.__recvBucket = (el.getAttribute("data-bucket") || "").toLowerCase();
        document.querySelectorAll(".o-recv-expand.open").forEach((tr) => {
          tr.classList.remove("open");
          tr.dataset.loaded = "0";
        });
        document.querySelectorAll(".o_example_cards .o_card").forEach((c) => c.classList.remove("active"));
        el.classList.add("active");
      });
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    if (!document.querySelector(".o_mssql_recv")) return;
    bindCards();
    bindExpand();
  });
})();
