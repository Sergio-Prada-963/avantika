/** @odoo-module **/
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";

const INDICATORS = [
    { key: "verde", label: "Verde", colorClass: "bg-success-subtle text-success-emphasis", filterName: "move_indicator_verde" },
    { key: "amarillo", label: "Amarillo", colorClass: "bg-warning-subtle text-warning-emphasis", filterName: "move_indicator_amarillo" },
    { key: "rojo", label: "Rojo", colorClass: "bg-danger-subtle text-danger-emphasis", filterName: "move_indicator_rojo" },
    { key: "negro", label: "Negro", colorClass: "bg-dark-subtle text-dark-emphasis", filterName: "move_indicator_negro" },
];

export class MoveDashboard extends Component {
    static template = "stock_picking_custom.MoveDashboard";
    static props = { list: { type: Object, optional: true } };

    setup() {
        this.orm = useService("orm");
        this.indicators = INDICATORS;

        onWillStart(async () => {
            await this.updateDashboardState(this.props);
        });
        onWillUpdateProps(async (nextProps) => {
            // Dentro de onWillUpdateProps, `this.props` todavía son los
            // props VIEJOS (los nuevos llegan solo por este argumento), así
            // que hay que usar `nextProps`, no `this.props`.
            await this.updateDashboardState(nextProps);
        });
    }

    async updateDashboardState(props) {
        const domain = props.list?.domain || [];
        this.counts = await this.orm.call("stock.move", "retrieve_move_dashboard", [domain]);
    }

    getCount(key) {
        return (this.counts && this.counts[key]) || 0;
    }

    /**
     * Limpia la búsqueda actual y activa el filtro del indicador en el que
     * se hizo click.
     */
    setSearchContext(ev) {
        const filterName = ev.currentTarget.getAttribute("filter_name");
        const searchItems = this.env.searchModel.getSearchItems((item) =>
            item.name === filterName
        );
        this.env.searchModel.query = [];
        for (const item of searchItems) {
            this.env.searchModel.toggleSearchItem(item.id);
        }
    }
}
