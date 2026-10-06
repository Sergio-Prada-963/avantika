/** @odoo-module **/
import { registry } from "@web/core/registry";
import {
    QtyAtDatePopover,
    QtyAtDateWidget,
    qtyAtDateWidget,
} from "@sale_stock/widgets/qty_at_date_widget";

// Mismo widget que el nativo, pero el botón "Ver Pronóstico" del popover abre
// nuestra propia acción cliente (ver demand_forecasted.js), que agrega los
// datos de TODAS las bodegas en vez de limitarse a la de la orden de venta.
export class DemandQtyAtDatePopover extends QtyAtDatePopover {
    openForecast() {
        this.actionService.doAction("purchase_sale_demand.action_demand_forecasted_product_product", {
            additionalContext: {
                active_model: "product.product",
                active_id: this.props.record.data.product_id.id,
                move_to_match_ids: this.props.record.data.move_ids.currentIds,
                sale_line_to_match_id: this.props.record.resId,
            },
        });
    }
}

export class DemandQtyAtDateWidget extends QtyAtDateWidget {
    static components = { Popover: DemandQtyAtDatePopover };
}

export const demandQtyAtDateWidget = {
    component: DemandQtyAtDateWidget,
    fieldDependencies: qtyAtDateWidget.fieldDependencies,
};

registry.category("view_widgets").add("demand_qty_at_date_widget", demandQtyAtDateWidget);
