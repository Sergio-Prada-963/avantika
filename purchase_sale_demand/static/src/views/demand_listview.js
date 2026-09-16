import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { DemandDashboard } from "@purchase_sale_demand/views/demand_dashboard";

export class DemandDashboardRenderer extends ListRenderer {
    static template = "purchase_sale_demand.ListRenderer";
    static components = { ...ListRenderer.components, DemandDashboard };
}

export const DemandDashboardListView = {
    ...listView,
    Renderer: DemandDashboardRenderer,
};

registry.category("views").add("demand_dashboard_list", DemandDashboardListView);
