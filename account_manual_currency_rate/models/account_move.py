# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Odoo's native invoice_currency_rate is a stored compute that depends on
    # invoice_date (among others): editing the date always retriggers it and
    # overwrites whatever rate the user had typed manually.
    #
    # `inverse` (not @api.onchange) is used to detect the manual edit: it is
    # called by the ORM itself whenever the field is written directly instead
    # of through its own compute callback -- both from a live form edit and
    # from a plain write() -- so it does not depend on how/when the web
    # client happens to dispatch onchange RPCs for a given field.
    invoice_currency_rate = fields.Float(inverse='_inverse_invoice_currency_rate')
    invoice_currency_rate_is_manual = fields.Boolean(copy=False)

    def _inverse_invoice_currency_rate(self):
        for move in self:
            move.invoice_currency_rate_is_manual = True

    @api.onchange('currency_id')
    def _onchange_currency_id_reset_manual_rate(self):
        for move in self:
            move.invoice_currency_rate_is_manual = False

    def _compute_invoice_currency_rate(self):
        manual_moves = self.filtered('invoice_currency_rate_is_manual')
        preserved_rates = {move.id: move.invoice_currency_rate for move in manual_moves}
        super()._compute_invoice_currency_rate()
        for move in manual_moves:
            move.invoice_currency_rate = preserved_rates[move.id]

    def refresh_invoice_currency_rate(self):
        res = super().refresh_invoice_currency_rate()
        self.invoice_currency_rate_is_manual = False
        return res
