# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # Native currency_rate is a plain compute field (no readonly=False), so
    # it is not editable by the user. Unlock it, duplicating the same
    # editable-rate pattern account.move uses for invoice_currency_rate.
    currency_rate = fields.Float(readonly=False)

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

    # Purchase has no pricelist-driven "Update Prices" button like sale.order
    # (vendor prices come from product.supplierinfo, not a pricelist), and
    # line price_unit is not recomputed when the order's currency changes
    # (currency_id/currency_rate are not in
    # _compute_price_unit_and_date_planned_and_name's depends). Duplicate the
    # same "suggest + manual trigger" UX as sale's Update Prices button.
    show_update_currency_rate_prices = fields.Boolean(store=False)

    @api.onchange('currency_id')
    def _onchange_currency_id_show_update_prices(self):
        if self.order_line and self._origin.currency_id != self.currency_id:
            self.show_update_currency_rate_prices = True

    def _convert_to_order_currency_with_manual_rate(self, amount, from_currency, date):
        """Like from_currency._convert(amount, self.currency_id, ...), but the
        final leg from company currency to the order currency uses the
        manual `currency_rate` instead of always looking up the table."""
        self.ensure_one()
        company_currency = self.company_id.currency_id
        if from_currency != company_currency:
            # No manual override exists for this pair; fall back to the table
            # only to bring the amount into company currency first.
            amount = from_currency._convert(amount, company_currency, self.company_id, date, False)
        if self.currency_id == company_currency:
            return amount
        rate = self.currency_rate or self.expected_currency_rate
        return self.currency_id.round(amount * rate)

    def action_update_prices(self):
        # Does NOT reuse _compute_price_unit_and_date_planned_and_name
        # directly: that method silently skips a line whenever it already
        # has a price and there is no seller-specific pricing to convert
        # from — exactly the common case, which made the button appear to
        # do nothing. A button the user clicks on purpose should always
        # recompute, so the same pricing formulas are applied here
        # unconditionally instead, using the manual currency_rate rather
        # than a fresh table lookup.
        AccountTax = self.env['account.tax']
        for order in self:
            lines = order.order_line.filtered(lambda l: l.product_id and not l.display_type and not l.invoice_lines)
            for line in lines:
                date = order.date_order or fields.Date.context_today(line)
                if line.selected_seller_id:
                    seller = line.selected_seller_id
                    new_price = AccountTax._fix_tax_included_price_company(
                        seller.price, line.product_id.supplier_taxes_id, line.tax_ids, line.company_id)
                    new_price = order._convert_to_order_currency_with_manual_rate(new_price, seller.currency_id, date)
                    new_price = seller.product_uom_id._compute_price(new_price, line.product_uom_id)
                else:
                    po_line_uom = line.product_uom_id or line.product_id.uom_id
                    new_price = AccountTax._fix_tax_included_price_company(
                        line.product_id.uom_id._compute_price(line.product_id.standard_price, po_line_uom),
                        line.product_id.supplier_taxes_id, line.tax_ids, line.company_id)
                    new_price = order._convert_to_order_currency_with_manual_rate(new_price, line.product_id.cost_currency_id, date)
                line._reset_price_unit(new_price)
            order.show_update_currency_rate_prices = False

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        if self.currency_id != self.company_id.currency_id:
            invoice_vals['invoice_currency_rate'] = self.currency_rate
        return invoice_vals
