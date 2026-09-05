# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    # Same self-contained editable-rate pattern as account.payment
    # (models/account_payment.py in this module), so the payment can be
    # created with a manually edited rate from the start.
    expected_currency_rate = fields.Float(
        compute='_compute_expected_currency_rate',
        digits=0,
    )
    # Plain editable field refreshed via onchange (not a stored compute
    # depending on a non-stored field, which was leaving this at 0).
    manual_currency_rate = fields.Float(
        string="Currency Rate",
        digits=0,
    )

    @api.depends('currency_id', 'company_id', 'payment_date')
    def _compute_expected_currency_rate(self):
        for wizard in self:
            if wizard.currency_id:
                wizard.expected_currency_rate = self.env['res.currency']._get_conversion_rate(
                    from_currency=wizard.company_id.currency_id,
                    to_currency=wizard.currency_id,
                    company=wizard.company_id,
                    date=wizard.payment_date,
                )
            else:
                wizard.expected_currency_rate = 1

    @api.onchange('currency_id', 'company_id', 'payment_date')
    def _onchange_reset_manual_currency_rate(self):
        for wizard in self:
            wizard.manual_currency_rate = wizard.expected_currency_rate

    def refresh_manual_currency_rate(self):
        for wizard in self:
            wizard.manual_currency_rate = wizard.expected_currency_rate

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        if self.currency_id != self.company_id.currency_id:
            # Never let a stale/unset rate slip through as 0.
            payment_vals['manual_currency_rate'] = self.manual_currency_rate or self.expected_currency_rate
        return payment_vals
