# -*- coding: utf-8 -*-
from odoo import api, fields, models

# Separador poco común, para no chocar con nombres de ubicación que puedan
# traer comas, guiones, etc. (ej. "WH/Stock", "Almacen - Principal").
LOCATION_QTY_SEPARATOR = "¦"

MOVE_INDICATOR_SELECTION = [
    ('verde', "Verde"),
    ('amarillo', "Amarillo"),
    ('rojo', "Rojo"),
    ('negro', "Negro"),
]

# Mismo dominio que usa la acción "Movimientos Pendientes" (ver
# views/stock_move_pending_views.xml): se repite aquí porque el cron y el
# dashboard necesitan buscar sobre stock.move en Python, no en la vista.
PENDING_MOVE_DOMAIN = [
    '&', '&',
    ('location_id.usage', 'in', ('internal', 'transit')),
    ('location_dest_id.usage', 'not in', ('internal', 'transit')),
    ('state', 'not in', ['done', 'cancel']),
]


class StockMove(models.Model):
    _inherit = 'stock.move'

    move_indicator = fields.Selection(
        MOVE_INDICATOR_SELECTION,
        string="Indicador de Atraso",
        compute='_compute_move_indicator',
        store=True,
        help="Semáforo según los días de atraso entre la fecha límite "
             "(date_deadline) y hoy, comparado contra los umbrales "
             "configurados en Inventario > Configuración > Ajustes. Se "
             "recalcula al cambiar la fecha límite o la configuración, y "
             "todos los días vía la acción planificada (solo para "
             "movimientos pendientes).",
    )
    move_indicator_days = fields.Integer(
        string="Días de Atraso",
        compute='_compute_move_indicator',
        store=True,
        aggregator=None,
        help="Días de atraso respecto a la fecha límite (negativo si la "
             "fecha límite todavía no llega); es el número que se muestra "
             "en la primera columna, coloreado según move_indicator.",
    )

    @api.depends(
        'date_deadline',
        'company_id.stock_move_indicador_verde',
        'company_id.stock_move_indicador_amarillo',
        'company_id.stock_move_indicador_rojo',
        'company_id.stock_move_indicador_negro',
    )
    def _compute_move_indicator(self):
        today = fields.Date.context_today(self)
        for move in self:
            if not move.date_deadline:
                move.move_indicator = False
                move.move_indicator_days = 0
                continue

            days = (today - move.date_deadline.date()).days
            company = move.company_id or self.env.company

            if days <= company.stock_move_indicador_verde:
                indicator = 'verde'
            elif days <= company.stock_move_indicador_amarillo:
                indicator = 'amarillo'
            elif days <= company.stock_move_indicador_rojo:
                indicator = 'rojo'
            else:
                indicator = 'negro'
            move.move_indicator = indicator
            move.move_indicator_days = days

    @api.model
    def _cron_recompute_move_indicator(self):
        moves = self.search(PENDING_MOVE_DOMAIN)
        moves._compute_move_indicator()

    @api.model
    def retrieve_move_dashboard(self, domain=None):
        """Cantidad de movimientos pendientes agrupados por
        `move_indicator`, para las cajas de resumen sobre el listado de
        Movimientos Pendientes.

        `domain` es el dominio actual y completo de la vista (ya incluye el
        domain base de la acción más los filtros/búsqueda que el usuario
        tenga aplicados), para que las cajas cuenten exactamente los
        registros que se están viendo en ese momento."""
        domain = domain or []
        groups = self._read_group(domain, ['move_indicator'], ['__count'])
        counts = {key: 0 for key, _label in self._fields['move_indicator'].selection}
        for indicator, count in groups:
            if indicator:
                counts[indicator] = count
        return counts

    product_location_qty_display = fields.Char(
        string="Disponibilidad por Ubicación",
        compute='_compute_product_location_qty_display',
        help="Lista de 'Ubicación - Cantidad' con las existencias actuales "
             "del producto de este movimiento, en todas las ubicaciones "
             "internas donde haya algo (positivo o negativo). La muestra el "
             "widget product_location_qty_tags como etiquetas.",
    )

    @api.depends('product_id.qty_available')
    def _compute_product_location_qty_display(self):
        # Se depende de product_id.qty_available solo como disparador (es
        # el campo que Odoo invalida cada vez que cambia algo en
        # stock.quant/stock.move): el valor en sí se arma aparte, agregando
        # directamente los quants del producto.
        for move in self:
            if not move.product_id:
                move.product_location_qty_display = False
                continue
            quants = self.env['stock.quant'].search([
                ('product_id', '=', move.product_id.id),
                ('location_id.usage', '=', 'internal'),
                ('quantity', '!=', 0),
            ])
            uom = move.product_id.uom_id
            parts = [
                "%s - %s" % (quant.location_id.display_name, uom.round(quant.quantity))
                for quant in quants.sorted(key=lambda q: q.location_id.display_name)
            ]
            move.product_location_qty_display = LOCATION_QTY_SEPARATOR.join(parts)
