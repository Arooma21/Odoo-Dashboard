# -*- coding: utf-8 -*-
{
    "name": "mssql_bridge",
    "version": "18.0.1.1.4",  # bump version for cache-busting
    "summary": "MSSQL Receivables Dashboard & Charts",
    "license": "LGPL-3",
    "depends": ["base", "web"],
    "data": [
        "views/menu_action.xml",
        "views/recv_dashboard_templates.xml",
        "views/recv_charts_templates.xml",
        "views/recv_bucket_page.xml",
    ],
    "assets": {
        "web.assets_backend": [
            # Styles (shared)
            "mssql_bridge/static/src/scss/recv_dashboard.scss",

            # Chart.js (local copy)
            "mssql_bridge/static/lib/chartjs/chart.umd.js",

            # JS: charts page
            "mssql_bridge/static/src/js/recv_charts_render.js",

            # JS: dashboard interactions
            "mssql_bridge/static/src/js/recv_dashboard_expand.js",
            "mssql_bridge/static/src/js/recv_dashboard_refresh.js",
            "mssql_bridge/static/src/js/recv_dashboard_filter.js",
        ],
    },
    "installable": True,
}
