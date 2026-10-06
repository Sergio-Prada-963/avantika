# -*- coding: utf-8 -*-
from odoo import models


class StockForecastedProductProductDemand(models.AbstractModel):
    _name = 'purchase.sale.demand.forecasted.product.product'
    _inherit = ['stock.forecasted_product_product']
    _description = "Disponibilidad en Todas las Bodegas (Compra por Demanda)"

    def _get_all_warehouses(self):
        return self.env['stock.warehouse'].search([
            ('company_id', 'in', self.env.companies.ids),
        ])

    def _get_report_data(self, product_template_ids=False, product_ids=False):
        assert product_template_ids or product_ids
        res = {}

        warehouses = self._get_all_warehouses()
        all_wh_location_ids = [loc['id'] for loc in self.env['stock.location'].search_read(
            [('id', 'child_of', warehouses.mapped('view_location_id').ids)],
            ['id'],
        )]

        # El resumen (a la mano/entrante/saliente/pronosticado) se calcula
        # UNA sola vez con las ubicaciones de TODAS las bodegas: los campos
        # nativos de producto (qty_available, free_qty, virtual_available,
        # incoming_qty, outgoing_qty) que lee _get_report_header ya son
        # globales por compañía cuando no hay contexto de bodega/ubicación
        # (ver product._get_domain_locations), así que esto basta para que
        # el resumen sea el total real, no el de una sola bodega.
        res.update(self._get_report_header(product_template_ids, product_ids, all_wh_location_ids))

        # Las tablas de detalle (disponible/reservado) sí dependen de una
        # única "wh_stock_location" por cada corrida del algoritmo nativo de
        # reconciliación (no se pueden fusionar varias bodegas en una sola
        # pasada sin reescribir ese algoritmo), así que se corre una vez POR
        # BODEGA -reusando tal cual la lógica nativa de cada una- y luego se
        # concatenan los resultados, marcando de qué bodega viene cada línea.
        lines = []
        for warehouse in warehouses:
            wh_location_ids = [loc['id'] for loc in self.env['stock.location'].search_read(
                [('id', 'child_of', warehouse.view_location_id.id)],
                ['id'],
            )]
            wh_lines = super()._get_report_lines(
                product_template_ids, product_ids, wh_location_ids, warehouse.lot_stock_id,
            )
            for line in wh_lines:
                self._tag_line_with_warehouse(line, warehouse)
            lines += wh_lines

        res['lines'] = lines
        res['user_can_edit_pickings'] = self.env.user.has_group('stock.group_stock_user')
        return res

    def _tag_line_with_warehouse(self, line, warehouse):
        # No se modifican document_in['name']/document_out['name']: esos
        # mismos valores los usa el JS nativo (_sameDocument en
        # forecasted_details.js) para decidir si dos líneas son "el mismo
        # documento" al fusionar filas visualmente - alterarlos rompería esa
        # comparación. En su lugar se agrega una clave nueva, que la
        # plantilla propia (demand_forecasted_details.xml) muestra aparte.
        line['warehouse_name'] = warehouse.name
