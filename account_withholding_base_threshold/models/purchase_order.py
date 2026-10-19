# -*- coding: utf-8 -*-
from odoo import Command, api, models
from odoo.tools import float_compare

ORDER_LINE_TRIGGER_FIELDS = (
    'order_line',
    'order_line.price_subtotal',
    'order_line.tax_ids',
    'order_line.product_qty',
    'order_line.price_unit',
)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.onchange(*ORDER_LINE_TRIGGER_FIELDS, 'fiscal_position_id')
    def _onchange_sync_uvt_withholding_taxes(self):
        for order in self:
            order._sync_uvt_withholding_taxes()

    @api.model_create_multi
    def create(self, vals_list):
        # purchase.order.fiscal_position_id NO es un campo computado
        # guardado (a diferencia de sale.order/account.move): el núcleo
        # solo lo llena vía un @api.onchange('partner_id') que jamás se
        # dispara al crear la orden por código (como hace
        # purchase_sale_demand). Sin esto, toda orden de compra creada así
        # quedaría con fiscal_position_id vacío, y cualquier impuesto con
        # posición fiscal configurada nunca podría aplicarse en ella.
        for vals in vals_list:
            if vals.get('partner_id') and not vals.get('fiscal_position_id'):
                partner = self.env['res.partner'].browse(vals['partner_id'])
                vals['fiscal_position_id'] = self.env['account.fiscal.position']._get_fiscal_position(partner).id
        orders = super().create(vals_list)
        orders._sync_uvt_withholding_taxes()
        return orders

    def write(self, vals):
        res = super().write(vals)
        if {'order_line', 'partner_id', 'currency_id', 'fiscal_position_id'} & set(vals.keys()):
            self._sync_uvt_withholding_taxes()
        return res

    def button_confirm(self):
        # Final safety net, mirroring account.move's _post() guard.
        self._sync_uvt_withholding_taxes()
        return super().button_confirm()

    def _sync_uvt_withholding_taxes(self):
        for order in self:
            # Solo se gestionan los impuestos que este módulo considera
            # "configurados": uvt_base, o el campo nativo de Odoo "Posición
            # fiscal" (fiscal_position_ids) en el propio impuesto. Un
            # impuesto sin NINGUNO de estos dos campos -el predeterminado
            # del producto, por ejemplo- queda completamente intocado, con
            # su comportamiento normal. No se filtra por is_reteica aquí:
            # purchase.order nunca tuvo un campo city_declaration_id (es
            # exclusivo de ventas/facturas), así que esa regla no aplica a
            # compras, igual que antes de este cambio.
            candidate_taxes = self.env['account.tax'].search([
                *self.env['account.tax']._check_company_domain(order.company_id),
                ('type_tax_use', '=', 'purchase'),
                '|',
                ('uvt_base', '=', True),
                ('fiscal_position_ids', '!=', False),
            ])
            for tax in candidate_taxes:
                # Regla 1 (posición fiscal): se compara contra la posición
                # fiscal de la ORDEN (fiscal_position_id), no la del
                # contacto directamente. En condiciones normales coinciden
                # (ver create() más arriba y el onchange nativo), pero si se
                # sobreescribe a mano en esta orden específica, se respeta
                # esa elección. Un impuesto sin fiscal_position_ids
                # configurado siempre pasa esta regla; uno con posiciones
                # configuradas solo pasa si la orden tiene exactamente
                # alguna de esas posiciones.
                if tax.fiscal_position_ids and order.fiscal_position_id not in tax.fiscal_position_ids:
                    order._set_tax_on_all_lines(tax, False)
                    continue

                # Regla 2 (umbral UVT): si no está activa, el impuesto ya
                # pasó la regla de posición fiscal y se aplica directamente.
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


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _apply_uvt_withholding_tax(self, tax, should_have_tax):
        self.ensure_one()
        has_tax = tax in self.tax_ids
        if should_have_tax and not has_tax:
            self.tax_ids = [Command.link(tax.id)]
        elif not should_have_tax and has_tax:
            self.tax_ids = [Command.unlink(tax.id)]
