{
    "name": "mssql_bridge",
    "version": "18.0.1.1.3",  # bump the version
    "summary": "MSSQL Receivables Dashboard (no JS assets)",
    "license": "LGPL-3",
    "depends": ["base", "web"],
'data': [
    'views/menu_action.xml',
    'views/recv_dashboard_templates.xml',
    'views/recv_charts_templates.xml',
],
'assets': {
    'web.assets_backend': [
        # ✅ Keep your styles (shared by dashboard + charts)
        'mssql_bridge/static/src/scss/recv_dashboard.scss',

        # ✅ Chart.js library (local file you placed in static/lib/chartjs)
        'mssql_bridge/static/lib/chartjs/chart.umd.js',

        # ✅ JS that draws the charts (either recv_charts_render.js or recv_charts.js)
        'mssql_bridge/static/src/js/recv_charts_render.js',

        # NEW: expandable invoices on dashboard
        'mssql_bridge/static/src/js/recv_dashboard_expand.js',
        'mssql_bridge/static/src/js/recv_dashboard_refresh.js',
        'mssql_bridge/static/src/js/recv_dashboard_filter.js',
    ],
},


}
