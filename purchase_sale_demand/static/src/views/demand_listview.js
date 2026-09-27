import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { DemandDashboard } from "@purchase_sale_demand/views/demand_dashboard";

// Los <widget> de una lista no reciben una clase CSS propia por nombre (a
// diferencia de los <field>), así que no hay forma de acercar con CSS puro
// las celdas de los íconos de gráfica/lupa sin este pequeño override.
const ICON_WIDGET_NAMES = ["qty_at_date_widget", "stock_quant_search_widget"];

export class DemandDashboardRenderer extends ListRenderer {
    static template = "purchase_sale_demand.ListRenderer";
    static components = { ...ListRenderer.components, DemandDashboard };

    getCellClass(column, record) {
        const classNames = super.getCellClass(column, record);
        if (column.type === "widget" && ICON_WIDGET_NAMES.includes(column.name)) {
            return `${classNames} o_demand_icon_cell`;
        }
        return classNames;
    }
}

export const DemandDashboardListView = {
    ...listView,
    Renderer: DemandDashboardRenderer,
};

registry.category("views").add("demand_dashboard_list", DemandDashboardListView);
