/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, xml } from "@odoo/owl";

/**
 * Guaranteed-safe placeholder component.
 * It renders a tiny message so the UI never blanks out.
 * Your real component in recv_dashboard.js will override this with the same key.
 */
class RecvDashboardPlaceholder extends Component {}
RecvDashboardPlaceholder.template = xml/* xml */ `
  <div class="p-3">
    <h3>Receivables (Live)</h3>
    <p>Loading dashboard…</p>
  </div>
`;

// If the action isn’t registered yet, register the placeholder.
const actions = registry.category("actions");
if (!actions.contains("mssql_bridge.recv_dashboard")) {
  actions.add("mssql_bridge.recv_dashboard", RecvDashboardPlaceholder);
  console.log("[mssql_bridge] boot.js registered placeholder component");
}
