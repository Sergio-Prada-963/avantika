# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    trm = fields.Float(
        string='TRM',
        compute='_compute_trm',
        digits=(16, 5),
        help="Unidades de la moneda de la compañía equivalentes a 1 unidad "
             "de la moneda de este documento, según la tasa de cambio "
             "vigente en la fecha de la factura (o de contabilización, si la "
             "primera no está definida). Si el documento ya está en la "
             "moneda de la compañía, este valor siempre es 1.",
    )

    @api.depends('currency_id', 'company_id', 'invoice_date', 'date')
    def _compute_trm(self):
        for move in self:
            date = move.invoice_date or move.date or fields.Date.context_today(move)
            move.trm = move.currency_id._get_conversion_rate(
                move.currency_id, move.company_id.currency_id, move.company_id, date,
            )
