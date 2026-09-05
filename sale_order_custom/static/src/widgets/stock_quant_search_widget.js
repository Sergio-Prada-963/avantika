import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { _t } from "@web/core/l10n/translation";

export class StockQuantSearchWidget extends Component {
    static template = "sale_order_custom.StockQuantSearchWidget";
    static props = { ...standardWidgetProps };

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
    }

    get isVisible() {
        return Boolean(this.props.record.data.display_qty_widget) || this.isKit;
    }

    get hasProduct() {
        return Boolean(this.props.record.data.product_id);
    }

    get isKit() {
        return Boolean(this.props.record.data.product_is_kit);
    }

    async openQuants(ev) {
        ev.preventDefault();
        const product = this.props.record.data.product_id;
        if (!product) {
            return;
        }
        if (this.isKit) {
            const action = await this.orm.call(
                "sale.order.line",
                "action_view_kit_stock",
                [product.id]
            );
            await this.actionService.doAction(action);
            return;
        }
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            name: _t("Existencias por Ubicación"),
            res_model: "stock.quant",
            view_mode: "list",
            views: [[false, "list"]],
            domain: [
                ["product_id", "=", product.id],
                ["location_id.usage", "=", "internal"],
            ],
        });
    }

    async openSupplierInfo(ev) {
        ev.preventDefault();
        const product = this.props.record.data.product_id;
        if (!product) {
            return;
        }
        const action = await this.orm.call(
            "sale.order.line",
            "action_open_supplierinfo_for_product",
            [product.id]
        );
        await this.actionService.doAction(action);
    }

    async openBom(ev) {
        ev.preventDefault();
        const product = this.props.record.data.product_id;
        if (!product) {
            return;
        }
        const action = await this.orm.call(
            "sale.order.line",
            "action_view_kit_components",
            [product.id]
        );
        await this.actionService.doAction(action);
    }
}

export const stockQuantSearchWidget = {
    component: StockQuantSearchWidget,
    fieldDependencies: [
        { name: "display_qty_widget", type: "boolean" },
        { name: "product_is_kit", type: "boolean" },
    ],
};

registry.category("view_widgets").add("stock_quant_search_widget", stockQuantSearchWidget);
