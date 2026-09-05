# -*- coding: utf-8 -*-
from odoo import Command, api, fields, models
from odoo.tools import float_compare

ORDER_LINE_TRIGGER_FIELDS = (
    'order_line',
    'order_line.price_subtotal',
    'order_line.tax_ids',
    'order_line.product_uom_qty',
    'order_line.price_unit',
    'order_line.discount',
)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    city_declaration_id = fields.Many2one(
        'res.city',
        string='Ciudad Declaración ReteICA',
        compute='_compute_city_declaration_id',
        store=True, readonly=False,
        help="Municipio en el que se declara el ReteICA de esta orden. Se "
             "toma por defecto del cliente, pero puede sobreescribirse si "
             "esta operación específica debe declararse en otra ciudad.",
    )

    @api.depends('partner_id')
    def _compute_city_declaration_id(self):
        for order in self:
            order.city_declaration_id = order.partner_id.city_declaration_id

    @api.onchange(*ORDER_LINE_TRIGGER_FIELDS, 'city_declaration_id')
    def _onchange_sync_uvt_withholding_taxes(self):
        for order in self:
            order._sync_uvt_withholding_taxes()

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders._sync_uvt_withholding_taxes()
        return orders

    def write(self, vals):
        res = super().write(vals)
        if {'order_line', 'partner_id', 'currency_id', 'city_declaration_id'} & set(vals.keys()):
            self._sync_uvt_withholding_taxes()
        return res

    def action_confirm(self):
        # Final safety net, mirroring account.move's _post() guard.
        self._sync_uvt_withholding_taxes()
        return super().action_confirm()

    def _prepare_invoice(self):
        values = super()._prepare_invoice()
        values['city_declaration_id'] = self.city_declaration_id.id
        return values

    def _sync_uvt_withholding_taxes(self):
        for order in self:
            uvt_value = order.company_id.uvt_value
            if uvt_value <= 0:
                continue
            candidate_taxes = self.env['account.tax'].search([
                *self.env['account.tax']._check_company_domain(order.company_id),
                ('uvt_base', '=', True),
                ('type_tax_use', '=', 'sale'),
            ])
            for tax in candidate_taxes:
                if tax.is_reteica and tax.city_id != order.city_declaration_id:
                    # ReteICA de otro municipio (o no hay ciudad declarada):
                    # nunca aplica en esta orden, sin importar la base.
                    order._remove_tax_from_lines(tax)
                    continue
                order._sync_single_uvt_withholding_tax(tax, uvt_value)

    def _remove_tax_from_lines(self, tax):
        self.ensure_one()
        for line in self.order_line.filtered(lambda l: not l.display_type):
            line._apply_uvt_withholding_tax(tax, False)

    def _sync_single_uvt_withholding_tax(self, tax, uvt_value):
        self.ensure_one()
        minimum = tax.uvt_quantity * uvt_value
        rounding = self.currency_id.rounding or 0.01
        lines = self.order_line.filtered(lambda l: not l.display_type)

        if tax.uvt_base_type == 'total':
            base = sum(lines.mapped('price_subtotal'))
            meets_threshold = float_compare(base, minimum, precision_rounding=rounding) >= 0
            for line in lines:
                line._apply_uvt_withholding_tax(tax, meets_threshold)
        else:
            for line in lines:
                meets_threshold = float_compare(
                    line.price_subtotal, minimum, precision_rounding=rounding
                ) >= 0
                line._apply_uvt_withholding_tax(tax, meets_threshold)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _apply_uvt_withholding_tax(self, tax, should_have_tax):
        self.ensure_one()
        has_tax = tax in self.tax_ids
        if should_have_tax and not has_tax:
            self.tax_ids = [Command.link(tax.id)]
        elif not should_have_tax and has_tax:
            self.tax_ids = [Command.unlink(tax.id)]
