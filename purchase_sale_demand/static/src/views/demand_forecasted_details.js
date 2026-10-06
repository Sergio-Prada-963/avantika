/** @odoo-module **/
import { ForecastedDetails } from "@stock/stock_forecasted/forecasted_details";

// El template nativo muestra "Existencias libres" como una etiqueta fija
// (sin referencia a la línea ni al producto), así que agregar el nombre de
// la bodega ahí requiere convertir el getter en un método que reciba la
// línea (ver demand_forecasted_details.xml, que llama a freeStockLabel(line)
// en vez de freeStockLabel). Para "Disponible"/"Usado por" (document_in /
// document_out) el propio template agrega el sufijo " - <bodega>" aparte,
// sin tocar line.document_in.name / line.document_out.name (esos los usa
// _sameDocument para fusionar filas del mismo documento).
export class DemandForecastedDetails extends ForecastedDetails {
    static template = "purchase_sale_demand.DemandForecastedDetails";

    freeStockLabel(line) {
        const label = super.freeStockLabel;
        if (line && line.warehouse_name) {
            return `${label} - ${line.warehouse_name}`;
        }
        return label;
    }
}
