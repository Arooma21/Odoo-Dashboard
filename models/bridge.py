# -*- coding: utf-8 -*-
import pyodbc
from odoo import api, models, _
from odoo.exceptions import UserError


class MssqlBridge(models.TransientModel):
    _name = "mssql.bridge"
    _description = "MSSQL Bridge Utilities (Sage 300 AROBL)"

    # -------------------------------------------------------------------------
    # Connection helpers
    # -------------------------------------------------------------------------
    @api.model
    def _param(self, key, required=True, default=None):
        v = self.env["ir.config_parameter"].sudo().get_param(key, default)
        if required and not v:
            raise UserError(_("Missing system parameter: %s") % key)
        return v

    @api.model
    def _connect(self):
        server = self._param("mssql.server")
        database = self._param("mssql.database")
        username = self._param("mssql.username")
        password = self._param("mssql.password")
        driver = self._param("mssql.driver", required=False, default="ODBC Driver 18 for SQL Server")
        conn_str = (
            f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};UID={username};PWD={password};"
            "Encrypt=yes;TrustServerCertificate=yes;"
        )
        try:
            return pyodbc.connect(conn_str, timeout=10)
        except Exception as e:
            raise UserError(_("MSSQL connection failed: %s") % e)

    # -------------------------------------------------------------------------
    # Aging by customer (used by dashboard + charts)
    # -------------------------------------------------------------------------
    @api.model
    def get_aging_by_customer(self):
        """
        Return one row per customer with bucketed balances (open amounts only).
        Keys: customer_code, customer_name, current, d0_30, d31_60, d61_90, d90p, total
        """
        sql = """
            WITH ar AS (
                SELECT
                    ob.IDCUST AS customer_code,
                    cu.NAMECUST AS customer_name,
                    CAST(ob.AMTDUEHC AS DECIMAL(18,2)) AS balance,
                    -- DATEDUE is DECIMAL(YYYYMMDD). Cast to INT, then to varchar(8), then to DATE (style 112).
                    TRY_CONVERT(date, CONVERT(varchar(8), CAST(ob.DATEDUE AS int)), 112) AS due_date
                FROM AROBL ob
                JOIN ARCUS cu ON cu.IDCUST = ob.IDCUST
                -- include *open* items of any sign; ignore zeroes
                WHERE (ob.SWPAID IN ('0', 0) OR ob.SWPAID IS NULL)
                  AND ABS(ob.AMTDUEHC) <> 0
            )
            SELECT
                customer_code,
                MAX(customer_name) AS customer_name,
                SUM(CASE WHEN DATEDIFF(day, due_date, GETDATE()) < 0  THEN balance ELSE 0 END) AS current_amt,
                SUM(CASE WHEN DATEDIFF(day, due_date, GETDATE()) BETWEEN 0  AND 30 THEN balance ELSE 0 END) AS d0_30,
                SUM(CASE WHEN DATEDIFF(day, due_date, GETDATE()) BETWEEN 31 AND 60 THEN balance ELSE 0 END) AS d31_60,
                SUM(CASE WHEN DATEDIFF(day, due_date, GETDATE()) BETWEEN 61 AND 90 THEN balance ELSE 0 END) AS d61_90,
                SUM(CASE WHEN DATEDIFF(day, due_date, GETDATE()) > 90 THEN balance ELSE 0 END) AS d90p,
                SUM(balance) AS total_amt
            FROM ar
            GROUP BY customer_code
            HAVING ABS(SUM(balance)) > 0.005
            ORDER BY customer_code;
        """

        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(sql)
            cols = [d[0].lower() for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]

            for rec in rows:
                rec["current"] = rec.pop("current_amt", 0) or 0.0
                rec["d0_30"]   = rec.get("d0_30", 0) or 0.0
                rec["d31_60"]  = rec.get("d31_60", 0) or 0.0
                rec["d61_90"]  = rec.get("d61_90", 0) or 0.0
                rec["d90p"]    = rec.get("d90p", 0) or 0.0
                rec["total"]   = rec.pop("total_amt", 0) or 0.0

            return rows
        except Exception as e:
            raise UserError(_("AROBL query failed: %s") % e)
        finally:
            try:
                conn.close()
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # Invoices for a customer — open items only (use AMTDUEHC)
    # Returns: DATEINVC (from DATEDUE), IDORDERNBR, IDCUSTPO, DESCINVC, AMTINVCHC(open)
    # -------------------------------------------------------------------------
    # models/bridge.py  (inside class MssqlBridge)

    @api.model
    def get_invoices_basic_by_customer(self, customer_code=None, customer_name=None):
        """
        Return open invoices (positive or credit) for a customer.
        Matches by code and/or exact name (after trimming).
        Fields returned:
          DATEINVC (from DATEDUE for readability), IDORDERNBR, IDCUSTPO, DESCINVC, AMTINVCHC (= AMTDUEHC)
        """
        code = (customer_code or "").strip()
        name = (customer_name or "").strip()

        conds, params = [], []
        if code:
            conds.append("LTRIM(RTRIM(bl.IDCUST)) = LTRIM(RTRIM(?))")
            params.append(code)
        if name:
            conds.append("LTRIM(RTRIM(cu.NAMECUST)) = LTRIM(RTRIM(?))")
            params.append(name)

        if not conds:
            return []

        where_clause = " AND (" + " OR ".join(conds) + ")"

        sql = f"""
            SELECT
                -- user-friendly date: due date
                TRY_CONVERT(date, CONVERT(varchar(8), CAST(bl.DATEDUE AS int)), 112) AS DATEINVC,
                bl.IDORDERNBR,
                bl.IDCUSTPO,
                bl.DESCINVC,
                CAST(bl.AMTDUEHC AS DECIMAL(18,2)) AS AMTINVCHC
            FROM AROBL bl
            JOIN ARCUS cu ON cu.IDCUST = bl.IDCUST
            WHERE (bl.SWPAID IN ('0', 0) OR bl.SWPAID IS NULL)  -- open items
              AND ABS(bl.AMTDUEHC) <> 0                         -- include credits
              {where_clause}
            ORDER BY DATEINVC DESC, bl.IDORDERNBR;
        """

        conn = self._connect()
        rows = []
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            for DATEINVC, IDORDERNBR, IDCUSTPO, DESCINVC, AMTINVCHC in cur.fetchall():
                rows.append({
                    "DATEINVC": DATEINVC.isoformat() if DATEINVC else "",
                    "IDORDERNBR": str(IDORDERNBR or ""),
                    "IDCUSTPO": str(IDCUSTPO or ""),
                    "DESCINVC": DESCINVC or "",
                    "AMTINVCHC": float(AMTINVCHC or 0.0),
                })
            return rows
        finally:
            try:
                conn.close()
            except Exception:
                pass

