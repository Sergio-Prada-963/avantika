/** @odoo-module **/
import { registry } from "@web/core/registry";
import { BadgeField, badgeField } from "@web/views/fields/badge/badge_field";

// Copia de web.BadgeField que sí muestra el badge cuando el valor es 0: el
// widget nativo usa `t-if="props.record.data[props.name]"` (comprobación de
// verdad), así que un entero en 0 (p. ej. move_indicator_days para un
// movimiento que vence hoy mismo) nunca se renderiza, aunque el dato sea
// perfectamente válido.
export class MoveDaysBadgeField extends BadgeField {
    static template = "stock_picking_custom.MoveDaysBadgeField";
}

export const moveDaysBadgeField = {
    ...badgeField,
    component: MoveDaysBadgeField,
};

registry.category("fields").add("move_days_badge", moveDaysBadgeField);
