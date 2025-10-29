# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# Labels used by the bucket page
BUCKETS = {
    "current": "Current",
    "d0_30": "1–30 Days",
    "d31_60": "31–60 Days",
    "d61_90": "61–90 Days",
    "d90p": "90+ Days",
}


def _read_json_payload():
    """Support both JSON-RPC and raw fetch() bodies."""
    try:
        if isinstance(getattr(request, "jsonrequest", None), (dict, list)):
            return request.jsonrequest or {}
    except Exception:
        pass
    try:
        raw = request.httprequest.data.decode("utf-8") if request.httprequest and request.httprequest.data else ""
        return json.loads(raw or "{}")
    except Exception:
        return {}


def _aggregate_totals(rows):
    t = {"current": 0.0, "d0_30": 0.0, "d31_60": 0.0, "d61_90": 0.0, "d90p": 0.0, "total": 0.0}
    for r in rows or []:
        t["current"] += float(r.get("current", 0) or 0)
        t["d0_30"] += float(r.get("d0_30", 0) or 0)
        t["d31_60"] += float(r.get("d31_60", 0) or 0)
        t["d61_90"] += float(r.get("d61_90", 0) or 0)
        t["d90p"] += float(r.get("d90p", 0) or 0)
        t["total"] += float(r.get("total", 0) or 0)
    return t


class RecvAPI(http.Controller):
    # ---------- JSON endpoints (optional) ----------
    @http.route("/recv/aging", type="json", auth="user")
    def recv_aging(self):
        rows = request.env["mssql.bridge"].sudo().get_aging_by_customer()
        return {"rows": rows, "totals": _aggregate_totals(rows)}

    @http.route("/recv/invoices", type="json", auth="user")
    def recv_invoices(self, **kw):
        payload = _read_json_payload()
        params = payload.get("params", payload) if isinstance(payload, dict) else {}
        code = (params.get("customer_code") or "").strip()
        name = (params.get("customer_name") or "").strip()
        bucket = (params.get("bucket") or "").strip().lower()

        if not (code or name):
            return {"rows": []}

        Bridge = request.env["mssql.bridge"].sudo()
        try:
            rows = Bridge.get_invoices_basic_by_customer(
                customer_code=code, customer_name=name, bucket=bucket
            ) or []
            return {"rows": rows}
        except Exception as e:
            _logger.exception("recv_invoices failed")
            return {"rows": [], "error": str(e)}

    # ---------- Pages ----------
    @http.route("/recv/dashboard", type="http", auth="user")
    def recv_dashboard_page(self, **kw):
        Bridge = request.env["mssql.bridge"].sudo()
        rows = Bridge.get_aging_by_customer()
        qcontext = {
            "rows": rows,
            "totals": _aggregate_totals(rows),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        return request.render("mssql_bridge.recv_dashboard_page", qcontext)

    @http.route("/recv/charts", type="http", auth="user")
    def recv_charts_page(self, **kw):
        Bridge = request.env["mssql.bridge"].sudo()
        rows = Bridge.get_aging_by_customer()
        totals = _aggregate_totals(rows)

        top10 = sorted(rows, key=lambda r: float(r.get("total") or 0), reverse=True)[:10]
        top10_labels = [(r.get("customer_name") or r.get("customer_code") or "-") for r in top10]
        top10_values = [float(r.get("total") or 0) for r in top10]

        return request.render(
            "mssql_bridge.recv_charts_page",
            {
                "totals_json": json.dumps(totals, ensure_ascii=False),
                "top10_labels_json": json.dumps(top10_labels, ensure_ascii=False),
                "top10_values_json": json.dumps(top10_values, ensure_ascii=False),
            },
        )

    @http.route("/recv/bucket/<string:bucket>", type="http", auth="user")
    def recv_bucket_page(self, bucket, **kw):
        b = (bucket or "").lower()
        if b not in BUCKETS:
            b = "d0_30"

        Bridge = request.env["mssql.bridge"].sudo()

        # 1) Exact customer universe + bucket amounts from the dashboard
        dash_rows = Bridge.get_aging_by_customer() or []

        rows = []
        for r in dash_rows:
            code = (r.get("customer_code") or "").strip()
            name = (r.get("customer_name") or "").strip()
            if not code and not name:
                continue

            # Bucket amount the dashboard used for THIS customer
            # (keys on your dashboard rows are already: current, d0_30, d31_60, d61_90, d90p)
            cust_bucket_amt = float(r.get(b) or 0.0)

            # If the customer's bucket nets to zero on the dashboard, skip them completely
            if abs(round(cust_bucket_amt, 3)) < 0.0005:
                continue

            invs = Bridge.get_invoices_basic_by_customer(
                customer_code=code,
                customer_name=name,
                bucket=b,
            ) or []

            # Lines subtotal for this customer in this bucket
            subtotal = round(sum(float(inv.get("AMTINVCHC") or 0.0) for inv in invs), 3)

            # If the fetched lines net to ~0, skip (offsetting invoice/credit not applied yet)
            if abs(subtotal) < 0.0005:
                continue

            for inv in invs:
                rows.append({
                    "customer_code": code,
                    "customer_name": name,
                    "IDINV": inv.get("IDINV"),
                    "DATEINVC": inv.get("DATEINVC"),
                    "DUE_DATE": inv.get("DUE_DATE"),
                    "IDORDERNBR": inv.get("IDORDERNBR"),
                    "IDCUSTPO": inv.get("IDCUSTPO"),
                    "DESCINVC": inv.get("DESCINVC"),
                    "AMTINVCHC": float(inv.get("AMTINVCHC") or 0.0),
                })

        # Sort and total (unchanged)
        rows.sort(key=lambda x: (x.get("customer_name") or "", x.get("DATEINVC") or "", x.get("IDINV") or ""),
                  reverse=True)
        total = round(sum(float(r.get("AMTINVCHC") or 0.0) for r in rows), 3)

        qcontext = {
            "bucket": b,
            "bucket_label": BUCKETS[b],
            "rows": rows,
            "total": total,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        return request.render("mssql_bridge.recv_bucket_page", qcontext)
