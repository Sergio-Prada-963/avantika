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

    @api.onchange(*ORDER_LINE_TRIGGER_FIELDS, 'city_declaration_id', 'fiscal_position_id')
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
        if {'order_line', 'partner_id', 'currency_id', 'city_declaration_id', 'fiscal_position_id'} & set(vals.keys()):
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
            # Solo se gestionan los impuestos que este módulo considera
            # "configurados": uvt_base, is_reteica, o el campo nativo de
            # Odoo "Posición fiscal" (fiscal_position_ids) en el propio
            # impuesto. Un impuesto sin NINGUNO de estos tres campos -el
            # predeterminado del producto, por ejemplo- queda completamente
            # intocado, con su comportamiento normal.
            candidate_taxes = self.env['account.tax'].search([
                *self.env['account.tax']._check_company_domain(order.company_id),
                ('type_tax_use', '=', 'sale'),
                '|', '|',
                ('uvt_base', '=', True),
                ('is_reteica', '=', True),
                ('fiscal_position_ids', '!=', False),
            ])
            for tax in candidate_taxes:
                # Regla 1 (posición fiscal): se compara contra la posición
                # fiscal de la ORDEN (fiscal_position_id), no la del
                # contacto directamente. En condiciones normales coinciden
                # (Odoo la precarga desde el contacto al crear/cambiar
                # partner_id), pero si se sobreescribe a mano en esta orden
                # específica, se respeta esa elección. Un impuesto sin
                # fiscal_position_ids configurado siempre pasa esta regla;
                # uno con posiciones configuradas solo pasa si la orden
                # tiene exactamente alguna de esas posiciones.
                if tax.fiscal_position_ids and order.fiscal_position_id not in tax.fiscal_position_ids:
                    order._set_tax_on_all_lines(tax, False)
                    continue

                # Regla 3 (ReteICA municipal): si está activa, el municipio
                # del impuesto debe coincidir con el declarado en la orden;
                # si no está activa, esta regla no bloquea nada.
                if tax.is_reteica and tax.city_id != order.city_declaration_id:
                    order._set_tax_on_all_lines(tax, False)
                    continue

                # Regla 2 (umbral UVT): si no está activa, el impuesto ya
                # pasó las otras dos compuertas y se aplica directamente.
                if not tax.uvt_base:
                    order._set_tax_on_all_lines(tax, True)
                    continue

                uvt_value = order.company_id.uvt_value
                if uvt_value <= 0:
                    # Sin UVT configurado no hay umbral que evaluar: se deja
                    # el impuesto tal como está (no se fuerza ni se quita).
                    continue
                order._sync_single_uvt_withholding_tax(tax, uvt_value)

    def _set_tax_on_all_lines(self, tax, should_have_tax):
        self.ensure_one()
        for line in self.order_line.filtered(lambda l: not l.display_type):
            line._apply_uvt_withholding_tax(tax, should_have_tax)

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
