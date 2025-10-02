{
    "name": "mssql_bridge",
    "version": "18.0.1.0.8",  # bump the version
    "summary": "MSSQL Receivables Dashboard (no JS assets)",
    "license": "LGPL-3",
    "depends": ["base", "web"],
    "data": [
        "views/menu_action.xml",
    ],
    # No web.assets_backend here — we don't need bundles for this approach
}
