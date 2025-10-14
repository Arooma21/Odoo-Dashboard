# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request
from datetime import datetime

class RecvAPI(http.Controller):

    def _aggregate_totals(self, rows):
        totals = {"current": 0.0, "d0_30": 0.0, "d31_60": 0.0, "d61_90": 0.0, "d90p": 0.0, "total": 0.0}
        for r in rows or []:
            totals["current"] += float(r.get("current", 0) or 0)
            totals["d0_30"]  += float(r.get("d0_30", 0) or 0)
            totals["d31_60"] += float(r.get("d31_60", 0) or 0)
            totals["d61_90"] += float(r.get("d61_90", 0) or 0)
            totals["d90p"]   += float(r.get("d90p", 0) or 0)
            totals["total"]  += float(r.get("total", 0) or 0)
        return totals

    # JSON endpoint (kept as-is)
    @http.route("/recv/aging", type="json", auth="user")
    def recv_aging(self):
        rows = request.env["mssql.bridge"].sudo().get_aging_by_customer()
        return {"rows": rows, "totals": self._aggregate_totals(rows)}

    # Dashboard page (your working one)
    @http.route("/recv/dashboard", type="http", auth="user")
    def recv_dashboard_page(self, **kw):
        rows = request.env["mssql.bridge"].sudo().get_aging_by_customer()
        qcontext = {
            "rows": rows,
            "totals": self._aggregate_totals(rows),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        return request.render("mssql_bridge.recv_dashboard_page", qcontext)

    # NEW: Charts-only page (separate URL)
    @http.route("/recv/charts", type="http", auth="user")
    def recv_charts_page(self, **kw):
        rows = request.env["mssql.bridge"].sudo().get_aging_by_customer()
        totals = self._aggregate_totals(rows)

        # Top 10 customers by total for the line chart
        top10 = sorted(rows, key=lambda r: float(r.get("total") or 0), reverse=True)[:10]
        top10_labels = [(r.get("customer_name") or r.get("customer_code") or "-") for r in top10]
        top10_values = [float(r.get("total") or 0) for r in top10]

        # Pass pre-serialized JSON (CSP-friendly, no inline logic needed)
        return request.render("mssql_bridge.recv_charts_page", {
            "totals_json": json.dumps(totals, ensure_ascii=False),
            "top10_labels_json": json.dumps(top10_labels, ensure_ascii=False),
            "top10_values_json": json.dumps(top10_values, ensure_ascii=False),
        })

    @http.route("/recv/invoices", type="json", auth="user")
    def recv_invoices(self, customer_code=None, customer_name=None):
        """
        Returns the invoice lines for the given customer.
        Your model method name may differ; adjust as needed.
        Expected return: list of dicts with keys:
           number, date, due_date, days_overdue, amount, bucket
        where 'bucket' in ["current","d0_30","d31_60","d61_90","d90p"]
        """
        if not (customer_code or customer_name):
            return {"rows": []}

        Bridge = request.env["mssql.bridge"].sudo()

        # Try a few common method names; replace with your own if you have it
        rows = []
        for meth in ("get_invoices_by_customer", "get_customer_invoices", "get_invoices"):
            fn = getattr(Bridge, meth, None)
            if fn:
                try:
                    rows = fn(customer_code=customer_code, customer_name=customer_name)
                    break
                except TypeError:
                    # fallback: some methods only accept one arg
                    try:
                        rows = fn(customer_code or customer_name)
                        break
                    except Exception:
                        pass

        # Ensure safe numeric + sane defaults
        norm = []
        for r in rows or []:
            norm.append({
                "number": r.get("number") or r.get("invoice") or "",
                "date": r.get("date") or "",
                "due_date": r.get("due_date") or "",
                "days_overdue": int(r.get("days_overdue") or 0),
                "amount": float(r.get("amount") or 0),
                "bucket": (r.get("bucket") or "").lower() or "current",
            })
        return {"rows": norm}
