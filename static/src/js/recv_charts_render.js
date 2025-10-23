/** @odoo-module **/

function parseJSON(id) {
  const el = document.getElementById(id);
  if (!el) return null;
  try { return JSON.parse(el.textContent || "null"); }
  catch { console.warn(`[mssql_bridge] Bad JSON in #${id}`); return null; }
}

const n = (v) => Number(v || 0); // force numeric
const fmt = (v) => n(v).toLocaleString(undefined, { maximumFractionDigits: 2 });
const shorten = (t, m = 24) => (t && t.length > m ? t.slice(0, m - 1) + "…" : (t || ""));

// Unified colors (map to ["Current","1–30","31–60","61–90","90+"])
const BUCKET_COLORS = [
  "#22c55e", // Current (green)
  "#facc15", // 1–30 (yellow)
  "#f97316", // 31–60 (amber)
  "#f87171", // 61-90 (red)
  "#ef4444", // 90+ (dark RED)
];

function renderCharts() {
  const Chart = window.Chart || globalThis.Chart;
  const totals = parseJSON("recv_totals_json");
  const top10Labels = (parseJSON("recv_top10_labels_json") || []).map((t) => shorten(t, 24));
  const top10Values = (parseJSON("recv_top10_values_json") || []).map(n);

  if (!Chart || !totals) return;

  // Buckets (coerced to numbers)
  const buckets = [n(totals.current), n(totals.d0_30), n(totals.d31_60), n(totals.d61_90), n(totals.d90p)];

  // Debug so we can see what Chart gets
  console.log("[mssql_bridge] buckets:", buckets);
  console.log("[mssql_bridge] top10:", top10Labels, top10Values);

  const axisGrid = { color: "rgba(0,0,0,0.06)" };
  const moneyTicks = { callback: (v) => fmt(v), autoSkip: true, maxTicksLimit: 6 };

  // ---------------- VERTICAL BAR (changed from horizontal) ----------------
  const barEl = document.getElementById("recv_bar");
  if (barEl) {
    new Chart(barEl, {
      type: "bar",
      data: {
        labels: ["Current","1–30","31–60","61–90","90+"],
        datasets: [{
          data: buckets,
          backgroundColor: BUCKET_COLORS,
          borderColor: BUCKET_COLORS,
          borderWidth: 1,
          barThickness: 20,
          maxBarThickness: 24,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        // indexAxis removed so X is category and Y is value (vertical bars)
        scales: {
          x: { grid: { display: false } },
          y: { beginAtZero: true, ticks: moneyTicks, grid: axisGrid },
        },
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: (ctx) => ` ${fmt(ctx.parsed.y)}` } }, // use Y since bars are vertical
        },
      },
    });
  }

  // ---------------- DOUGHNUT (90+ now red) ----------------
  const pieEl = document.getElementById("recv_pie");
  if (pieEl) {
    new Chart(pieEl, {
      type: "doughnut",
      data: {
        labels: ["Current","1–30","31–60","61–90","90+"],
        datasets: [{
          data: buckets,
          backgroundColor: BUCKET_COLORS, // includes red for 90+
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "60%",
        plugins: {
          legend: { position: "bottom" },
          tooltip: { callbacks: { label: (ctx) => ` ${ctx.label}: ${fmt(ctx.parsed)}` } },
        },
      },
    });
  }

  // ---------------- LINE ----------------
  const lineEl = document.getElementById("recv_line");
  if (lineEl && top10Labels.length && top10Values.length) {
    new Chart(lineEl, {
      type: "line",
      data: {
        labels: top10Labels,
        datasets: [{
          label: "Total",
          data: top10Values,
          borderColor: "#2563eb",
          backgroundColor: "rgba(37,99,235,0.15)",
          pointRadius: 2.5,
          tension: 0.3,
          fill: true,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { ticks: { autoSkip: true, maxTicksLimit: 10, maxRotation: 0 }, grid: { display: false } },
          y: { beginAtZero: true, ticks: moneyTicks, grid: axisGrid },
        },
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: (ctx) => ` ${fmt(ctx.parsed.y)}` } },
        },
      },
    });
  }
}

document.addEventListener("DOMContentLoaded", renderCharts);
