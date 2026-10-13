/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { TagsList } from "@web/core/tags_list/tags_list";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

// Colores cíclicos del mismo set que usan los many2many_tags nativos
// (o_tag_color_1..o_tag_color_11), para que cada ubicación se distinga a
// simple vista sin tener que diseñar una paleta propia.
const COLOR_COUNT = 11;

export class ProductLocationQtyTags extends Component {
    static template = "stock_picking_custom.ProductLocationQtyTags";
    static components = { TagsList };
    static props = { ...standardWidgetProps };

    get tags() {
        const value = this.props.record.data.product_location_qty_display;
        if (!value) {
            return [];
        }
        return value.split("¦").map((text, index) => ({
            id: index,
            text,
            colorIndex: (index % COLOR_COUNT) + 1,
        }));
    }
}

export const productLocationQtyTags = {
    component: ProductLocationQtyTags,
    fieldDependencies: [
        { name: "product_location_qty_display", type: "char" },
    ],
};

registry.category("view_widgets").add("product_location_qty_tags", productLocationQtyTags);
