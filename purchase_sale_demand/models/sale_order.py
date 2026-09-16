# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    already_purchased = fields.Boolean(
        string="Ya fue Comprado",
        compute='_compute_already_purchased',
        inverse='_inverse_already_purchased',
        store=True,
        help="Marca esta orden como ya comprada para que sus líneas dejen "
             "de aparecer en el listado de Compra por Demanda, aunque "
             "todavía tengan cantidad pendiente por comprar. Al marcar o "
             "desmarcar esta casilla se marca/desmarca en todas las líneas "
             "de la orden; y se recalcula sola (marcada solo si TODAS las "
             "líneas están marcadas) cada vez que cambia alguna línea.",
    )

    @api.depends('order_line.already_purchased', 'order_line.display_type', 'order_line.is_downpayment')
    def _compute_already_purchased(self):
        for order in self:
            lines = order.order_line.filtered(
                lambda l: not l.display_type and not l.is_downpayment
            )
            order.already_purchased = bool(lines) and all(lines.mapped('already_purchased'))

    def _inverse_already_purchased(self):
        for order in self:
            lines = order.order_line.filtered(
                lambda l: not l.display_type and not l.is_downpayment
            )
            lines.already_purchased = order.already_purchased
