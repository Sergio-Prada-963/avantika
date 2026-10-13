/** @odoo-module **/
import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { MoveDashboard } from "@stock_picking_custom/views/move_dashboard";

export class MoveDashboardRenderer extends ListRenderer {
    static template = "stock_picking_custom.ListRenderer";
    static components = { ...ListRenderer.components, MoveDashboard };
}

export const MoveDashboardListView = {
    ...listView,
    Renderer: MoveDashboardRenderer,
};

registry.category("views").add("move_dashboard_list", MoveDashboardListView);
