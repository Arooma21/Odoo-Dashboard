# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class RecvAPI(http.Controller):

    # JSON endpoint (keep if you want it for other uses)
    @http.route("/recv/aging", type="json", auth="user")
    def recv_aging(self):
        rows = request.env["mssql.bridge"].sudo().get_aging_by_customer()
        totals = {"current": 0, "d0_30": 0, "d31_60": 0, "d61_90": 0, "d90p": 0, "total": 0}
        for r in rows:
            for k in totals:
                totals[k] += float(r.get(k, 0) or 0)
        return {"rows": rows, "totals": totals}

    # HTML page for the dashboard (no assets needed)
    @http.route("/recv/dashboard", type="http", auth="user")
    def recv_dashboard_page(self, **kw):
        rows = request.env["mssql.bridge"].sudo().get_aging_by_customer()
        totals = {"current": 0, "d0_30": 0, "d31_60": 0, "d61_90": 0, "d90p": 0, "total": 0}
        for r in rows:
            for k in totals:
                totals[k] += float(r.get(k, 0) or 0)

        def fmt(n):  # simple HTML-safe formatter
            return f"{float(n or 0):,.2f}"

        # Build a minimal HTML table; no external JS/CSS required
        body = [
            "<div style='padding:16px;font-family:Inter,Arial,Helvetica,sans-serif'>",
            "<h2>Receivables (Live)</h2>",
            f"<div><b>Total:</b> {fmt(totals['total'])} | "
            f"0–30: {fmt(totals['d0_30'])} | 31–60: {fmt(totals['d31_60'])} | "
            f"61–90: {fmt(totals['d61_90'])} | 90+: {fmt(totals['d90p'])}</div>",
            "<table style='width:100%;border-collapse:collapse;margin-top:12px'>",
            "<thead><tr>",
            "<th style='text-align:left;border-bottom:1px solid #ddd;padding:6px'>Customer</th>",
            *[
                f"<th style='text-align:right;border-bottom:1px solid #ddd;padding:6px'>{h}</th>"
                for h in ["Current", "0–30", "31–60", "61–90", "90+", "Total"]
            ],
            "</tr></thead><tbody>",
        ]
        for r in rows:
            body.append("<tr>")
            body.append(
                f"<td style='padding:6px;border-bottom:1px solid #f0f0f0'>{(r.get('customer_name') or r.get('customer_code') or '')}</td>"
            )
            for key in ["current", "d0_30", "d31_60", "d61_90", "d90p", "total"]:
                body.append(
                    f"<td style='padding:6px;text-align:right;border-bottom:1px solid #f0f0f0'>{fmt(r.get(key, 0))}</td>"
                )
            body.append("</tr>")
        body.append("</tbody></table></div>")

        html = "<!doctype html><html><head><meta charset='utf-8'><title>Receivables (Live)</title></head><body>"
        html += "".join(body)
        html += "</body></html>"
        return request.make_response(html)
