# -*- coding: utf-8 -*-
import pyodbc
from odoo import api, models, _
from odoo.exceptions import UserError

class MssqlBridge(models.TransientModel):
    _name = "mssql.bridge"
    _description = "MSSQL Bridge Utilities (Sage 300 AROBL)"

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

    @api.model
    def get_aging_by_customer(self):
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
                WHERE ob.AMTDUEHC > 0
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
            ORDER BY customer_code;
        """

        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(sql)
            cols = [d[0].lower() for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]

            # normalize aliases for the frontend
            for rec in rows:
                rec["current"] = rec.pop("current_amt", 0)
                rec["total"] = rec.pop("total_amt", 0)

            return rows
        except Exception as e:
            # bubble a clear Odoo error
            raise UserError(_("AROBL query failed: %s") % e)
        finally:
            conn.close()
