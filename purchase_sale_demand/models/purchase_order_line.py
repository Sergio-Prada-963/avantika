# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    sale_line_id = fields.Many2one(
        'sale.order.line',
        string="Línea de Venta de Origen",
        index=True,
        help="Línea de venta que originó esta línea de compra, cuando la "
             "orden se generó automáticamente por demanda desde una venta. "
             "Una misma línea de venta puede tener varias líneas de compra "
             "asociadas (compras parciales).",
    )
    sale_order_ids = fields.Many2many(
        'sale.order',
        string="Orden de Venta",
        compute='_compute_sale_order_ids',
    )

    @api.depends('sale_line_id.order_id')
    def _compute_sale_order_ids(self):
        for line in self:
            line.sale_order_ids = line.sale_line_id.order_id
