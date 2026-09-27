import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";

const INDICATORS = [
    { key: "verde", label: "Verde", colorClass: "bg-success-subtle text-success-emphasis", filterName: "demand_indicator_verde" },
    { key: "amarillo", label: "Amarillo", colorClass: "bg-warning-subtle text-warning-emphasis", filterName: "demand_indicator_amarillo" },
    { key: "rojo", label: "Rojo", colorClass: "bg-danger-subtle text-danger-emphasis", filterName: "demand_indicator_rojo" },
    { key: "negro", label: "Negro", colorClass: "bg-dark-subtle text-dark-emphasis", filterName: "demand_indicator_negro" },
];

export class DemandDashboard extends Component {
    static template = "purchase_sale_demand.DemandDashboard";
    static props = { list: { type: Object, optional: true } };

    setup() {
        this.orm = useService("orm");
        this.indicators = INDICATORS;

        onWillStart(async () => {
            await this.updateDashboardState(this.props);
        });
        onWillUpdateProps(async (nextProps) => {
            // OJO: dentro de onWillUpdateProps, `this.props` todavía son los
            // props VIEJOS (los nuevos llegan solo por este argumento, Owl
            // no actualiza `this.props` hasta después de este hook). Si se
            // usa `this.props.list.domain` aquí, el dashboard siempre queda
            // un paso atrás y nunca refleja el filtro recién quitado/puesto.
            await this.updateDashboardState(nextProps);
        });
    }

    async updateDashboardState(props) {
        const domain = props.list?.domain || [];
        this.counts = await this.orm.call("sale.order.line", "retrieve_demand_dashboard", [domain]);
    }

    getCount(key, mine) {
        const bucket = mine ? this.counts?.my : this.counts?.global;
        return (bucket && bucket[key]) || 0;
    }

    /**
     * Limpia la búsqueda actual y activa el filtro del indicador en el
     * que se hizo click (junto con "Pendientes por Comprar", para que la
     * lista mostrada coincida con lo que cuenta la caja). Si se hizo click
     * en la fila "Mi", agrega además el filtro "Mis Compras" (proveedor
     * cuyo Comprador es el usuario actual).
     */
    setSearchContext(ev) {
        const filterName = ev.currentTarget.getAttribute("filter_name");
        const isMine = ev.currentTarget.getAttribute("mine") === "true";
        const filters = [filterName, "filter_pending_purchase"];
        if (isMine) {
            filters.push("filter_my_purchases");
        }
        const searchItems = this.env.searchModel.getSearchItems((item) =>
            filters.includes(item.name)
        );
        this.env.searchModel.query = [];
        for (const item of searchItems) {
            this.env.searchModel.toggleSearchItem(item.id);
        }
    }
}
