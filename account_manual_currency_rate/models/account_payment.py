# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # Independent from account.move's native invoice_currency_rate (that one
    # only applies to invoices). Applied to the journal entry in two ways:
    # - At move generation time (_generate_move_vals, below), via the native
    #   force_balance mechanism -- this is what fixes the entry created when
    #   the payment is confirmed, since Odoo only builds the move at that
    #   point and posts it in the same call.
    # - As a fallback for a move that already exists in draft (edited after
    #   creation, before confirming), the journal items' balance is rewritten
    #   directly (_apply_manual_currency_rate, below).
    manual_currency_rate = fields.Float(
        string="Currency Rate",
        digits=0,
        help="Exchange rate used for this payment. Defaults to the rate from "
             "the company's currency rate table for the payment date, but can "
             "be edited manually without altering that table.",
    )
    expected_currency_rate = fields.Float(
        compute='_compute_expected_currency_rate',
        digits=0,
    )

    @api.depends('currency_id', 'company_id', 'date')
    def _compute_expected_currency_rate(self):
        for payment in self:
            if payment.currency_id and payment.company_id:
                payment.expected_currency_rate = self.env['res.currency']._get_conversion_rate(
                    from_currency=payment.company_id.currency_id,
                    to_currency=payment.currency_id,
                    company=payment.company_id,
                    date=payment.date or fields.Date.context_today(payment),
                )
            else:
                payment.expected_currency_rate = 1

    @api.onchange('currency_id', 'company_id', 'date')
    def _onchange_reset_manual_currency_rate(self):
        for payment in self:
            payment.manual_currency_rate = payment.expected_currency_rate

    def refresh_manual_currency_rate(self):
        for payment in self:
            payment.manual_currency_rate = payment.expected_currency_rate

    @api.constrains('manual_currency_rate')
    def _check_manual_currency_rate(self):
        for payment in self:
            if (
                payment.currency_id
                and payment.company_id
                and payment.currency_id != payment.company_id.currency_id
                and payment.manual_currency_rate <= 0
            ):
                raise ValidationError(_("The currency rate must be strictly positive."))

    @api.model_create_multi
    def create(self, vals_list):
        payments = super().create(vals_list)
        payments._apply_manual_currency_rate()
        return payments

    def write(self, vals):
        res = super().write(vals)
        if {'manual_currency_rate', 'currency_id', 'amount', 'date'} & set(vals.keys()):
            self._apply_manual_currency_rate()
        return res

    def action_apply_manual_currency_rate(self):
        """Button: force a recalculation of the journal items' balance from
        the manual currency rate right now (in case it did not happen
        automatically for any reason)."""
        for payment in self:
            if payment.state != 'draft':
                raise UserError(_(
                    "The currency rate can only be applied while the payment "
                    "is in draft (%s).", payment.display_name,
                ))
        self._apply_manual_currency_rate()

    def _generate_move_vals(self, write_off_line_vals=None, force_balance=None, line_ids=None):
        # The journal entry is not created at payment creation time: Odoo
        # only generates it when the payment is confirmed (state -> 'in_process'),
        # and posts it in that same call. By the time `_apply_manual_currency_rate`
        # could react, the move is already posted and out of reach. Forcing the
        # liquidity line's balance here, at the exact point the lines are first
        # built, guarantees the move is created correctly from the start.
        self.ensure_one()
        if (
            force_balance is None
            and not line_ids
            and self.manual_currency_rate
            and self.currency_id
            and self.company_id
            and self.currency_id != self.company_id.currency_id
        ):
            force_balance = self.company_id.currency_id.round(abs(self.amount) / self.manual_currency_rate)
        return super()._generate_move_vals(
            write_off_line_vals=write_off_line_vals,
            force_balance=force_balance,
            line_ids=line_ids,
        )

    def _apply_manual_currency_rate(self):
        for payment in self:
            if (
                not payment.manual_currency_rate
                or not payment.move_id
                or not payment.company_id
                or not payment.currency_id
                or payment.currency_id == payment.company_id.currency_id
                or payment.move_id.state != 'draft'
            ):
                continue
            liquidity_lines, counterpart_lines, dummy_lines = payment._seek_for_lines()
            for line in liquidity_lines + counterpart_lines:
                if not line.amount_currency:
                    continue
                new_balance = payment.company_id.currency_id.round(
                    line.amount_currency / payment.manual_currency_rate
                )
                if line.balance != new_balance:
                    line.write({'balance': new_balance})
