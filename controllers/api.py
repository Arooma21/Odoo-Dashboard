# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class RecvAPI(http.Controller):

    # ----------------------------- helpers ---------------------------------
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

    # ------------------------------ JSON -----------------------------------
    @http.route("/recv/aging", type="json", auth="user")
    def recv_aging(self):
        rows = request.env["mssql.bridge"].sudo().get_aging_by_customer()
        return {"rows": rows, "totals": self._aggregate_totals(rows)}

    # --------------------------- Dashboard page -----------------------------
    @http.route("/recv/dashboard", type="http", auth="user")
    def recv_dashboard_page(self, **kw):
        Bridge = request.env["mssql.bridge"].sudo()
        rows = Bridge.get_aging_by_customer()
        qcontext = {
            "rows": rows,
            "totals": self._aggregate_totals(rows),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        return request.render("mssql_bridge.recv_dashboard_page", qcontext)

    # ----------------------------- Charts page ------------------------------
    @http.route("/recv/charts", type="http", auth="user")
    def recv_charts_page(self, **kw):
        Bridge = request.env["mssql.bridge"].sudo()
        rows = Bridge.get_aging_by_customer()
        totals = self._aggregate_totals(rows)

        top10 = sorted(rows, key=lambda r: float(r.get("total") or 0), reverse=True)[:10]
        top10_labels = [(r.get("customer_name") or r.get("customer_code") or "-") for r in top10]
        top10_values = [float(r.get("total") or 0) for r in top10]

        return request.render("mssql_bridge.recv_charts_page", {
            "totals_json": json.dumps(totals, ensure_ascii=False),
            "top10_labels_json": json.dumps(top10_labels, ensure_ascii=False),
            "top10_values_json": json.dumps(top10_values, ensure_ascii=False),
        })

    # ------------------------- AJAX: customer invoices ----------------------
    @http.route("/recv/invoices", type="json", auth="user")
    def recv_invoices(self, **kw):
        """
        Works with either {"params": {...}} or plain {...}.
        Returns list of dicts with keys:
          DATEINVC, IDORDERNBR, IDCUSTPO, DESCINVC, AMTINVCHC
        """
        # --- Fix for environments without request.jsonrequest ---
        try:
            data = getattr(request, "jsonrequest", None)
            if not data:
                import json
                data = json.loads(request.httprequest.data.decode("utf-8") or "{}")
        except Exception:
            data = {}

        params = data.get("params", data) if isinstance(data, dict) else {}

        code = (params.get("customer_code") or "").strip()
        name = (params.get("customer_name") or "").strip()

        _logger.info("[recv_invoices] code=%r name=%r", code, name)

        if not (code or name):
            return {"rows": []}

        Bridge = request.env["mssql.bridge"].sudo()
        try:
            rows = Bridge.get_invoices_basic_by_customer(
                customer_code=code,
                customer_name=name,
            ) or []
        except Exception as e:
            _logger.exception("Error fetching invoices from MSSQL")
            return {"rows": [], "error": str(e)}

        return {"rows": rows}
