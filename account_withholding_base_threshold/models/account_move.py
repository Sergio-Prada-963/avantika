# -*- coding: utf-8 -*-
from odoo import Command, api, fields, models
from odoo.tools import float_compare

INVOICE_LINE_TRIGGER_FIELDS = (
    'invoice_line_ids',
    'invoice_line_ids.price_subtotal',
    'invoice_line_ids.tax_ids',
    'invoice_line_ids.quantity',
    'invoice_line_ids.price_unit',
    'invoice_line_ids.discount',
)
MOVE_TYPE_TAX_USE = {
    'out_invoice': 'sale',
    'out_refund': 'sale',
    'in_invoice': 'purchase',
    'in_refund': 'purchase',
}


class AccountMove(models.Model):
    _inherit = 'account.move'

    city_declaration_id = fields.Many2one(
        'res.city',
        string='Ciudad Declaración ReteICA',
        compute='_compute_city_declaration_id',
        store=True, readonly=False,
        help="Municipio en el que se declara el ReteICA de esta factura. Se "
             "toma por defecto del cliente (o de la orden de venta de "
             "origen), pero puede sobreescribirse si esta operación "
             "específica debe declararse en otra ciudad.",
    )

    @api.depends('partner_id')
    def _compute_city_declaration_id(self):
        for move in self:
            move.city_declaration_id = move.partner_id.city_declaration_id

    @api.onchange(*INVOICE_LINE_TRIGGER_FIELDS, 'city_declaration_id', 'fiscal_position_id')
    def _onchange_sync_uvt_withholding_taxes(self):
        for move in self:
            if move.state == 'draft' and move.is_invoice(include_receipts=True):
                move._sync_uvt_withholding_taxes()

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        moves.filtered(
            lambda m: m.state == 'draft' and m.is_invoice(include_receipts=True)
        )._sync_uvt_withholding_taxes()
        return moves

    def write(self, vals):
        res = super().write(vals)
        if {'invoice_line_ids', 'partner_id', 'currency_id', 'city_declaration_id', 'fiscal_position_id'} & set(vals.keys()):
            self.filtered(
                lambda m: m.state == 'draft' and m.is_invoice(include_receipts=True)
            )._sync_uvt_withholding_taxes()
        return res

    def _post(self, soft=True):
        # Final safety net: covers any path that changed lines/taxes without
        # going through create()/write() on this model (e.g. direct SQL,
        # or a flow that only touches account.move.line).
        self.filtered(
            lambda m: m.state == 'draft' and m.is_invoice(include_receipts=True)
        )._sync_uvt_withholding_taxes()
        return super()._post(soft=soft)

    def _sync_uvt_withholding_taxes(self):
        for move in self:
            type_tax_use = MOVE_TYPE_TAX_USE.get(move.move_type)
            if not type_tax_use:
                continue

            # Solo se gestionan los impuestos que este módulo considera
            # "configurados": uvt_base, is_reteica, o el campo nativo de
            # Odoo "Posición fiscal" (fiscal_position_ids) en el propio
            # impuesto. Un impuesto sin NINGUNO de estos tres campos -el
            # predeterminado del producto, por ejemplo- queda completamente
            # intocado, con su comportamiento normal.
            candidate_taxes = self.env['account.tax'].search([
                *self.env['account.tax']._check_company_domain(move.company_id),
                ('type_tax_use', '=', type_tax_use),
                '|', '|',
                ('uvt_base', '=', True),
                ('is_reteica', '=', True),
                ('fiscal_position_ids', '!=', False),
            ])
            for tax in candidate_taxes:
                # Regla 1 (posición fiscal): se compara contra la posición
                # fiscal del DOCUMENTO (fiscal_position_id), no la del
                # contacto directamente. En condiciones normales coinciden
                # (Odoo la precarga desde el contacto al crear/cambiar
                # partner_id), pero si se sobreescribe a mano en este
                # documento específico, se respeta esa elección. Un impuesto
                # sin fiscal_position_ids configurado siempre pasa esta
                # regla; uno con posiciones configuradas solo pasa si el
                # documento tiene exactamente alguna de esas posiciones.
                if tax.fiscal_position_ids and move.fiscal_position_id not in tax.fiscal_position_ids:
                    move._set_tax_on_all_lines(tax, False)
                    continue

                # Regla 3 (ReteICA municipal): si está activa, el municipio
                # del impuesto debe coincidir con el declarado en la
                # factura; si no está activa, esta regla no bloquea nada.
                if tax.is_reteica and tax.city_id != move.city_declaration_id:
                    move._set_tax_on_all_lines(tax, False)
                    continue

                # Regla 2 (umbral UVT): si no está activa, el impuesto ya
                # pasó las otras dos compuertas y se aplica directamente.
                if not tax.uvt_base:
                    move._set_tax_on_all_lines(tax, True)
                    continue

                uvt_value = move.company_id.uvt_value
                if uvt_value <= 0:
                    # Sin UVT configurado no hay umbral que evaluar: se deja
                    # el impuesto tal como está (no se fuerza ni se quita).
                    continue
                move._sync_single_uvt_withholding_tax(tax, uvt_value)

    def _set_tax_on_all_lines(self, tax, should_have_tax):
        self.ensure_one()
        for line in self.invoice_line_ids:
            line._apply_uvt_withholding_tax(tax, should_have_tax)

    def _sync_single_uvt_withholding_tax(self, tax, uvt_value):
        self.ensure_one()
        minimum = tax.uvt_quantity * uvt_value
        rounding = self.currency_id.rounding or 0.01

        if tax.uvt_base_type == 'total':
            base = sum(self.invoice_line_ids.mapped('price_subtotal'))
            meets_threshold = float_compare(base, minimum, precision_rounding=rounding) >= 0
            for line in self.invoice_line_ids:
                line._apply_uvt_withholding_tax(tax, meets_threshold)
        else:
            # 'lines': each line is evaluated on its own, independently of
            # the others -- a line's tax is added/removed as soon as ITS OWN
            # subtotal crosses the threshold.
            for line in self.invoice_line_ids:
                meets_threshold = float_compare(
                    line.price_subtotal, minimum, precision_rounding=rounding
                ) >= 0
                line._apply_uvt_withholding_tax(tax, meets_threshold)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _apply_uvt_withholding_tax(self, tax, should_have_tax):
        self.ensure_one()
        has_tax = tax in self.tax_ids
        if should_have_tax and not has_tax:
            self.tax_ids = [Command.link(tax.id)]
        elif not should_have_tax and has_tax:
            self.tax_ids = [Command.unlink(tax.id)]
