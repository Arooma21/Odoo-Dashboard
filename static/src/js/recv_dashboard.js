/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, xml, useState, onMounted } from "@odoo/owl";
import { jsonrpc } from "@web/core/network/rpc_service";

class RecvDashboard extends Component {
  static template = xml/* xml */`
    <div class="o_form_view o_mssql_recv" style="padding:16px">
      <h2>Receivables (Live)</h2>

      <t t-if="state.loading"><p>Loading…</p></t>
      <t t-elif="state.error"><div class="alert alert-danger"><t t-esc="state.error"/></div></t>

      <t t-else="">
        <div t-if="state.totals">
          <strong>Total:</strong> <t t-esc="fmt(state.totals.total)"/> |
          0–30: <t t-esc="fmt(state.totals.d0_30)"/> |
          31–60: <t t-esc="fmt(state.totals.d31_60)"/> |
          61–90: <t t-esc="fmt(state.totals.d61_90)"/> |
          90+: <t t-esc="fmt(state.totals.d90p)"/>
        </div>

        <table class="table table-sm table-striped mt-3">
          <thead>
            <tr>
              <th>Customer</th>
              <th class="text-end">Current</th>
              <th class="text-end">0–30</th>
              <th class="text-end">31–60</th>
              <th class="text-end">61–90</th>
              <th class="text-end">90+</th>
              <th class="text-end">Total</th>
            </tr>
          </thead>
          <tbody>
            <t t-foreach="state.rows" t-as="r" t-key="r.customer_code">
              <tr>
                <td><t t-esc="r.customer_name || r.customer_code"/></td>
                <td class="text-end"><t t-esc="fmt(r.current)"/></td>
                <td class="text-end"><t t-esc="fmt(r.d0_30)"/></td>
                <td class="text-end"><t t-esc="fmt(r.d31_60)"/></td>
                <td class="text-end"><t t-esc="fmt(r.d61_90)"/></td>
                <td class="text-end"><t t-esc="fmt(r.d90p)"/></td>
                <td class="text-end"><t t-esc="fmt(r.total)"/></td>
              </tr>
            </t>
          </tbody>
        </table>
      </t>
    </div>
  `;

  setup() {
    this.state = useState({ loading: true, error: null, rows: [], totals: null });
    onMounted(() => this.reload());
  }

  async reload() {
    try {
      const resp = await jsonrpc("/recv/aging", {});
      this.state.rows = resp.rows || [];
      this.state.totals = resp.totals || null;
    } catch (e) {
      this.state.error = (e && e.message) || "Failed to load data";
    } finally {
      this.state.loading = false;
    }
  }

  fmt(n) {
    return Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
}

// REGISTER WITH NEW KEY
registry.category("actions").add("mssql_bridge.recv_dashboard_v2", RecvDashboard);
