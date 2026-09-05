# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Native currency_rate is a plain compute field (no readonly=False), so
    # it is not editable by the user. Unlock it, duplicating the same
    # editable-rate pattern account.move uses for invoice_currency_rate.
    currency_rate = fields.Float(readonly=False)

    # Native currency_id is also a plain compute (derived only from
    # pricelist_id): Sales normally expects the currency to come from
    # picking a pricelist denominated in that currency, not from a direct
    # field. Unlock it the same way, with the same inverse-based manual-edit
    # tracking already used for account.move.invoice_currency_rate, so
    # switching pricelist_id later doesn't silently discard the override.
    currency_id = fields.Many2one(readonly=False, inverse='_inverse_currency_id')
    currency_id_is_manual = fields.Boolean(copy=False)

    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        string="Company Currency",
    )
    expected_currency_rate = fields.Float(
        compute='_compute_expected_currency_rate',
        digits=0,
        help="Currency rate coming from the currency rate table for the order "
             "date. Shown for comparison with the (possibly manually edited) "
             "Currency Rate above.",
    )

    @api.depends('currency_id', 'date_order', 'company_id')
    def _compute_expected_currency_rate(self):
        for order in self:
            if order.currency_id:
                order.expected_currency_rate = self.env['res.currency']._get_conversion_rate(
                    from_currency=order.company_id.currency_id,
                    to_currency=order.currency_id,
                    company=order.company_id,
                    date=(order.date_order or fields.Datetime.now()).date(),
                )
            else:
                order.expected_currency_rate = 1

    @api.constrains('currency_rate')
    def _check_currency_rate(self):
        for order in self:
            if (
                order.currency_id
                and order.company_id
                and order.currency_id != order.company_id.currency_id
                and order.currency_rate <= 0
            ):
                raise ValidationError(_("The currency rate must be strictly positive."))

    def refresh_currency_rate(self):
        for order in self:
            order.currency_rate = order.expected_currency_rate

    def _inverse_currency_id(self):
        for order in self:
            order.currency_id_is_manual = True

    @api.onchange('currency_id')
    def _onchange_currency_id_show_update_prices(self):
        # Native show_update_pricelist / "Update Prices" button only reacts to
        # pricelist_id changes; extend it to also prompt when the currency is
        # overridden directly, since line prices are still in the old currency.
        if self.order_line and self._origin.currency_id != self.currency_id:
            self.show_update_pricelist = True

    @api.onchange('pricelist_id')
    def _onchange_pricelist_id_reset_manual_currency(self):
        for order in self:
            order.currency_id_is_manual = False

    def _compute_currency_id(self):
        manual_orders = self.filtered('currency_id_is_manual')
        preserved_currencies = {order.id: order.currency_id for order in manual_orders}
        super()._compute_currency_id()
        for order in manual_orders:
            order.currency_id = preserved_currencies[order.id]

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        if self.currency_id != self.company_id.currency_id:
            invoice_vals['invoice_currency_rate'] = self.currency_rate
        return invoice_vals
