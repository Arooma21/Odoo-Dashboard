# -*- coding: utf-8 -*-
{
    "name": "mssql_bridge",
    "version": "18.0.1.1.5",
    "summary": "MSSQL Receivables Dashboard & Charts",
    "license": "LGPL-3",
    "depends": ["base", "web"],

    "data": [
        "views/menu_action.xml",
        "views/recv_dashboard_templates.xml",
        "views/recv_charts_templates.xml",
        "views/recv_bucket_page.xml",
    ],

    # >>> put your assets in a dedicated bundle the pages will call explicitly
    "assets": {
        "web.assets_backend": [
            # styles
            "mssql_bridge/static/src/scss/recv_dashboard.scss",

            # libs (scoped, not global)
            "mssql_bridge/static/lib/chartjs/chart.umd.js",

            # js for each page
            "mssql_bridge/static/src/js/recv_charts_render.js",
            "mssql_bridge/static/src/js/recv_dashboard_expand.js",
            "mssql_bridge/static/src/js/recv_dashboard_refresh.js",
            "mssql_bridge/static/src/js/recv_dashboard_filter.js",
            "mssql_bridge/static/src/js/recv_bucket.js",
        ],
    },
    "installable": True,
}
