# -*- coding: utf-8 -*-
from odoo import fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    sale_line_id = fields.Many2one(
        'sale.order.line',
        string="Línea de Venta de Origen",
        index=True,
        help="Línea de venta que originó esta línea de compra, cuando la "
             "orden se generó automáticamente por demanda desde una venta, "
             "o que se vinculó manualmente después. Una misma línea de "
             "venta puede tener varias líneas de compra asociadas (compras "
             "parciales).",
    )
