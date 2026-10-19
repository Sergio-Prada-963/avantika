# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    trm = fields.Float(
        string='TRM',
        compute='_compute_trm',
        digits=(16, 5),
        help="Unidades de la moneda de la compañía equivalentes a 1 unidad "
             "de la moneda de esta orden, según la tasa de cambio vigente en "
             "la fecha de la orden. Si la orden ya está en la moneda de la "
             "compañía, este valor siempre es 1.",
    )

    @api.depends('currency_id', 'company_id', 'date_order')
    def _compute_trm(self):
        for order in self:
            date = (order.date_order or fields.Datetime.now()).date()
            order.trm = order.currency_id._get_conversion_rate(
                order.currency_id, order.company_id.currency_id, order.company_id, date,
            )
