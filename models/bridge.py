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
    # Aging by customer (dashboard totals)
    #  - 3 decimals
    #  - negative PY*/C* invoices forced to 'current'
    #  - include any non-zero customer total
    # -------------------------------------------------------------------------
    @api.model
    def get_aging_by_customer(self):
        sql = """
            WITH ar AS (
                SELECT
                    ob.IDCUST AS customer_code,
                    cu.NAMECUST AS customer_name,
                    CAST(ob.AMTDUEHC AS DECIMAL(18,3)) AS balance,
                    TRY_CONVERT(date, CONVERT(varchar(8), CAST(ob.DATEDUE AS int)), 112) AS due_date,
                    ob.IDINVC AS idinv,
                    CASE
                        WHEN (ob.IDINVC LIKE 'P%%' OR ob.IDINVC LIKE 'C%%') AND ob.AMTDUEHC < 0 THEN 'current'
                        WHEN DATEDIFF(day,
                               TRY_CONVERT(date, CONVERT(varchar(8), CAST(ob.DATEDUE AS int)), 112),
                               GETDATE()) < 0 THEN 'current'
                        WHEN DATEDIFF(day,
                               TRY_CONVERT(date, CONVERT(varchar(8), CAST(ob.DATEDUE AS int)), 112),
                               GETDATE()) BETWEEN 0 AND 30 THEN 'd0_30'
                        WHEN DATEDIFF(day,
                               TRY_CONVERT(date, CONVERT(varchar(8), CAST(ob.DATEDUE AS int)), 112),
                               GETDATE()) BETWEEN 31 AND 60 THEN 'd31_60'
                        WHEN DATEDIFF(day,
                               TRY_CONVERT(date, CONVERT(varchar(8), CAST(ob.DATEDUE AS int)), 112),
                               GETDATE()) BETWEEN 61 AND 90 THEN 'd61_90'
                        ELSE 'd90p'
                    END AS bucket
                FROM AROBL ob
                JOIN ARCUS cu ON cu.IDCUST = ob.IDCUST
                WHERE (ob.SWPAID IN ('0', 0) OR ob.SWPAID IS NULL)
                  AND ABS(ob.AMTDUEHC) <> 0
            )
            SELECT
                customer_code,
                MAX(customer_name) AS customer_name,
                SUM(CASE WHEN bucket = 'current' THEN balance ELSE 0 END) AS current_amt,
                SUM(CASE WHEN bucket = 'd0_30'  THEN balance ELSE 0 END) AS d0_30,
                SUM(CASE WHEN bucket = 'd31_60' THEN balance ELSE 0 END) AS d31_60,
                SUM(CASE WHEN bucket = 'd61_90' THEN balance ELSE 0 END) AS d61_90,
                SUM(CASE WHEN bucket = 'd90p'   THEN balance ELSE 0 END) AS d90p,
                SUM(balance) AS total_amt
            FROM ar
            GROUP BY customer_code
            HAVING ABS(SUM(balance)) > 0
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
    # Invoices for a single customer (used by expander) - same bucket rules
    # -------------------------------------------------------------------------
    @api.model
    def get_invoices_basic_by_customer(self, customer_code=None, customer_name=None, bucket=None):
        code = (customer_code or "").strip()
        name = (customer_name or "").strip()
        bkt  = (bucket or "").strip().lower()

        where, params = [], []
        if code:
            where.append("LTRIM(RTRIM(bl.IDCUST)) = LTRIM(RTRIM(?))")
            params.append(code)
        elif name:
            where.append("LTRIM(RTRIM(cu.NAMECUST)) = LTRIM(RTRIM(?))")
            params.append(name)
        else:
            return []

        bucket_case = """
            CASE
                WHEN (bl.IDINVC LIKE 'P%%' OR bl.IDINVC LIKE 'C%%') AND bl.AMTDUEHC < 0 THEN 'current'
                WHEN DATEDIFF(day, TRY_CONVERT(date, CONVERT(varchar(8), CAST(bl.DATEDUE AS int)), 112), GETDATE()) < 0  THEN 'current'
                WHEN DATEDIFF(day, TRY_CONVERT(date, CONVERT(varchar(8), CAST(bl.DATEDUE AS int)), 112), GETDATE()) BETWEEN 0  AND 30 THEN 'd0_30'
                WHEN DATEDIFF(day, TRY_CONVERT(date, CONVERT(varchar(8), CAST(bl.DATEDUE AS int)), 112), GETDATE()) BETWEEN 31 AND 60 THEN 'd31_60'
                WHEN DATEDIFF(day, TRY_CONVERT(date, CONVERT(varchar(8), CAST(bl.DATEDUE AS int)), 112), GETDATE()) BETWEEN 61 AND 90 THEN 'd61_90'
                ELSE 'd90p'
            END
        """

        bucket_filter = ""
        if bkt in ("current", "d0_30", "d31_60", "d61_90", "d90p"):
            bucket_filter = f" AND {bucket_case} = ? "
            params.append(bkt)

        sql = f"""
            SELECT
                bl.IDINVC                                               AS IDINV,
                TRY_CONVERT(date, CONVERT(varchar(8), CAST(bl.DATEDUE   AS int)), 112) AS DATEINVC,
                TRY_CONVERT(date, CONVERT(varchar(8), CAST(bl.DATEDUE   AS int)), 112) AS DUE_DATE,
                bl.IDORDERNBR,
                bl.IDCUSTPO,
                bl.DESCINVC,
                CAST(bl.AMTDUEHC AS DECIMAL(18,3))                      AS AMTINVCHC,
                {bucket_case}                                          AS bucket
            FROM AROBL bl
            {"JOIN ARCUS cu ON cu.IDCUST = bl.IDCUST" if name else ""}
            WHERE
                (bl.SWPAID IN ('0', 0) OR bl.SWPAID IS NULL)
                AND ABS(bl.AMTDUEHC) <> 0
                AND {" AND ".join(where)}
                {bucket_filter}
            ORDER BY DATEINVC DESC, bl.IDORDERNBR;
        """

        conn = self._connect()
        rows = []
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            for IDINV, DATEINVC, DUE_DATE, IDORDERNBR, IDCUSTPO, DESCINVC, AMTINVCHC, BK in cur.fetchall():
                rows.append({
                    "IDINV": str(IDINV or ""),
                    "DATEINVC": DATEINVC.isoformat() if hasattr(DATEINVC, "isoformat") else (str(DATEINVC) if DATEINVC else ""),
                    "DUE_DATE": DUE_DATE.isoformat() if hasattr(DUE_DATE, "isoformat") else (str(DUE_DATE) if DUE_DATE else ""),
                    "IDORDERNBR": str(IDORDERNBR or ""),
                    "IDCUSTPO": str(IDCUSTPO or ""),
                    "DESCINVC": DESCINVC or "",
                    "AMTINVCHC": float(AMTINVCHC or 0.0),
                    "bucket": (BK or "").lower(),
                })
            return rows
        except Exception as e:
            raise UserError(_("AROBL invoice query failed: %s") % e)
        finally:
            try:
                conn.close()
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # Bucket-wide invoices (bucket page) — EXACTLY match dashboard scope
    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # Bucket-wide invoices (used by /recv/bucket/<bucket> page)
    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # Bucket-wide invoices (EXACT mirror of dashboard bucketing)
    # -------------------------------------------------------------------------
    # models/bridge.py  (inside class MssqlBridge)

    @api.model
    def get_invoices_by_bucket(self, bucket):
        """
        Return ONLY the invoices that contribute to the dashboard totals for a given bucket.
        - 3 decimals
        - 'PY*' or 'C*' negatives are forced to 'current' (same as dashboard)
        - exclude customers whose net open balance == 0 (so page totals match the cards)
        """
        b = (bucket or "").strip().lower()
        if b not in ("current", "d0_30", "d31_60", "d61_90", "d90p"):
            b = "d0_30"

        bucket_case = """
            CASE
                WHEN (bl.IDINVC LIKE 'P%%' OR bl.IDINVC LIKE 'C%%') AND bl.AMTDUEHC < 0 THEN 'current'
                WHEN DATEDIFF(day,
                        TRY_CONVERT(date, CONVERT(varchar(8), CAST(bl.DATEDUE AS int)), 112),
                        GETDATE()) < 0 THEN 'current'
                WHEN DATEDIFF(day,
                        TRY_CONVERT(date, CONVERT(varchar(8), CAST(bl.DATEDUE AS int)), 112),
                        GETDATE()) BETWEEN 0  AND 30 THEN 'd0_30'
                WHEN DATEDIFF(day,
                        TRY_CONVERT(date, CONVERT(varchar(8), CAST(bl.DATEDUE AS int)), 112),
                        GETDATE()) BETWEEN 31 AND 60 THEN 'd31_60'
                WHEN DATEDIFF(day,
                        TRY_CONVERT(date, CONVERT(varchar(8), CAST(bl.DATEDUE AS int)), 112),
                        GETDATE()) BETWEEN 61 AND 90 THEN 'd61_90'
                ELSE 'd90p'
            END
        """

        sql = f"""
            /* 1) Same 'ar' CTE as dashboard (3 decimals + bucket rule) */
            WITH ar AS (
                SELECT
                    ob.IDCUST AS customer_code,
                    cu.NAMECUST AS customer_name,
                    CAST(ob.AMTDUEHC AS DECIMAL(18,3)) AS balance,
                    TRY_CONVERT(date, CONVERT(varchar(8), CAST(ob.DATEDUE AS int)), 112) AS due_date,
                    ob.IDINVC AS idinv,
                    CASE
                        WHEN (ob.IDINVC LIKE 'P%%' OR ob.IDINVC LIKE 'C%%') AND ob.AMTDUEHC < 0 THEN 'current'
                        WHEN DATEDIFF(day,
                               TRY_CONVERT(date, CONVERT(varchar(8), CAST(ob.DATEDUE AS int)), 112),
                               GETDATE()) < 0 THEN 'current'
                        WHEN DATEDIFF(day,
                               TRY_CONVERT(date, CONVERT(varchar(8), CAST(ob.DATEDUE AS int)), 112),
                               GETDATE()) BETWEEN 0 AND 30 THEN 'd0_30'
                        WHEN DATEDIFF(day,
                               TRY_CONVERT(date, CONVERT(varchar(8), CAST(ob.DATEDUE AS int)), 112),
                               GETDATE()) BETWEEN 31 AND 60 THEN 'd31_60'
                        WHEN DATEDIFF(day,
                               TRY_CONVERT(date, CONVERT(varchar(8), CAST(ob.DATEDUE AS int)), 112),
                               GETDATE()) BETWEEN 61 AND 90 THEN 'd61_90'
                        ELSE 'd90p'
                    END AS bucket
                FROM AROBL ob
                JOIN ARCUS cu ON cu.IDCUST = ob.IDCUST
                WHERE (ob.SWPAID IN ('0', 0) OR ob.SWPAID IS NULL)     -- open only
                  AND ABS(ob.AMTDUEHC) <> 0                            -- exclude true zeros
            ),
            /* 2) Restrict to the *same* customer set that appears on the dashboard */
            allowed_customers AS (
                SELECT customer_code
                FROM ar
                GROUP BY customer_code
                HAVING ABS(SUM(balance)) <> 0                          -- net open ≠ 0
            )

            /* 3) List invoices for those customers in the requested bucket */
            SELECT
                LTRIM(RTRIM(bl.IDCUST))                                  AS customer_code,
                cu.NAMECUST                                              AS customer_name,
                bl.IDINVC                                                AS IDINV,
                TRY_CONVERT(date, CONVERT(varchar(8), CAST(bl.DATEDUE AS int)), 112) AS DATEINVC,
                TRY_CONVERT(date, CONVERT(varchar(8), CAST(bl.DATEDUE AS int)), 112) AS DUE_DATE,
                bl.IDORDERNBR,
                bl.IDCUSTPO,
                bl.DESCINVC,
                CAST(bl.AMTDUEHC AS DECIMAL(18,3))                       AS AMTINVCHC
            FROM AROBL bl
            JOIN ARCUS cu ON cu.IDCUST = bl.IDCUST
            WHERE (bl.SWPAID IN ('0', 0) OR bl.SWPAID IS NULL)           -- open only
              AND ABS(bl.AMTDUEHC) <> 0
              AND LTRIM(RTRIM(bl.IDCUST)) IN (SELECT customer_code FROM allowed_customers)
              AND {bucket_case} = ?
            ORDER BY cu.NAMECUST, DATEINVC DESC, bl.IDINVC;
        """

        conn = self._connect()
        rows = []
        try:
            cur = conn.cursor()
            cur.execute(sql, [b])
            for rec in cur.fetchall():
                (customer_code, customer_name, IDINV, DATEINVC, DUE_DATE,
                 IDORDERNBR, IDCUSTPO, DESCINVC, AMTINVCHC) = rec
                rows.append({
                    "customer_code": (customer_code or "").strip(),
                    "customer_name": customer_name or "",
                    "IDINV": str(IDINV or ""),
                    "DATEINVC": DATEINVC.isoformat() if hasattr(DATEINVC, "isoformat") else (
                        str(DATEINVC) if DATEINVC else ""),
                    "DUE_DATE": DUE_DATE.isoformat() if hasattr(DUE_DATE, "isoformat") else (
                        str(DUE_DATE) if DUE_DATE else ""),
                    "IDORDERNBR": str(IDORDERNBR or ""),
                    "IDCUSTPO": str(IDCUSTPO or ""),
                    "DESCINVC": DESCINVC or "",
                    "AMTINVCHC": float(AMTINVCHC or 0.0),
                })
            return rows
        except Exception as e:
            raise UserError(_("AROBL invoice query failed: %s") % e)
        finally:
            try:
                conn.close()
            except Exception:
                pass


