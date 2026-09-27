import { registry } from "@web/core/registry";
import { BadgeField, badgeField } from "@web/views/fields/badge/badge_field";

// Copia de web.BadgeField que sí muestra el badge cuando el valor es 0: el
// widget nativo usa `t-if="props.record.data[props.name]"` (una comprobación
// de verdad), así que un entero en 0 (como demand_days para un pedido de
// hoy, 0 días transcurridos) nunca se renderiza, aunque el dato sea
// perfectamente válido.
export class DemandDaysBadgeField extends BadgeField {
    static template = "purchase_sale_demand.DemandDaysBadgeField";
}

export const demandDaysBadgeField = {
    ...badgeField,
    component: DemandDaysBadgeField,
};

registry.category("fields").add("demand_days_badge", demandDaysBadgeField);
