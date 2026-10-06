/** @odoo-module **/
import { registry } from "@web/core/registry";
import { StockForecasted } from "@stock/stock_forecasted/stock_forecasted";
import { DemandForecastedDetails } from "@purchase_sale_demand/views/demand_forecasted_details";
import { onWillStart } from "@odoo/owl";

// Variante de la acción cliente nativa "stock_forecasted" que ignora por
// completo la bodega: nunca fija `context.warehouse_id` (el nativo lo hace
// automáticamente si no viene en el contexto) y apunta al reporte Python
// propio (`purchase.sale.demand.forecasted.product.product`), que agrega
// resumen y tablas de TODAS las bodegas de la compañía.
export class DemandForecasted extends StockForecasted {
    static template = "purchase_sale_demand.DemandForecasted";
    static components = {
        ...StockForecasted.components,
        ForecastedDetails: DemandForecastedDetails,
    };

    setup() {
        super.setup();
        this.graphViewId = false;
        onWillStart(async () => {
            const [, viewId] = await this.orm.call(
                "ir.model.data", "check_object_reference",
                ["purchase_sale_demand", "stock_report_view_graph_demand"],
            );
            this.graphViewId = viewId;
        });
    }

    async _getReportValues() {
        await this._getResModel();
        this.reportModelName = "purchase.sale.demand.forecasted.product.product";
        const reportValues = await this.orm.call(this.reportModelName, "get_report_values", [], {
            context: this.context,
            docids: [this.productId],
        });
        this.docs = {
            ...reportValues.docs,
            ...reportValues.precision,
            lead_horizon_date: this.context.lead_horizon_date,
            qty_to_order: this.context.qty_to_order,
        };
    }

    get graphDomain() {
        const domain = [["state", "=", "forecast"]];
        if (this.resModel === "product.template") {
            domain.push(["product_tmpl_id", "=", this.productId]);
        } else {
            domain.push(["product_id", "=", this.productId]);
        }
        return domain;
    }
}

registry.category("actions").add("purchase_sale_demand_forecasted", DemandForecasted);
