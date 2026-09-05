# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, html_escape


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    allow_zero_margin_confirmation = fields.Boolean(
        string="Permitir Cotización en 0",
    )
    contract_global_due_date = fields.Date(
        string="Vencimiento Global del Contrato",
    )
    has_margin_lines = fields.Boolean(
        string="Tiene Líneas con Decisión de Margen",
        compute='_compute_has_margin_lines',
    )
    has_pending_margin_line = fields.Boolean(
        string="Tiene Líneas de Margen Pendientes",
        compute='_compute_has_margin_lines',
    )
    can_approve_sale_margin = fields.Boolean(
        string="Puede Aprobar Márgenes",
        compute='_compute_can_approve_sale_margin',
    )
    show_confirm_button = fields.Boolean(
        string="Mostrar Botón de Confirmar",
        compute='_compute_show_confirm_button',
    )

    @api.depends_context('uid')
    def _compute_show_confirm_button(self):
        show = self.env.user.show_confirm_button_sale
        for order in self:
            order.show_confirm_button = show

    @api.depends('order_line.display_type', 'order_line.margin_approval_status')
    def _compute_has_margin_lines(self):
        for order in self:
            decidable_lines = order.order_line.filtered(lambda l: not l.display_type)
            order.has_margin_lines = bool(decidable_lines)
            order.has_pending_margin_line = any(
                line.margin_approval_status == 'pending' for line in decidable_lines
            )

    @api.depends_context('uid')
    def _compute_can_approve_sale_margin(self):
        can_approve = self.env.user.approve_sale_margins
        for order in self:
            order.can_approve_sale_margin = can_approve

    @api.onchange('contract_global_due_date')
    def _onchange_contract_global_due_date(self):
        self.ensure_one()
        for line in self.order_line:
            line.due_date = self.contract_global_due_date

    def action_approve_all_margins(self):
        for order in self:
            order.order_line.filtered(lambda l: not l.display_type).action_approve_margin()

    def action_reject_all_margins(self):
        for order in self:
            order.order_line.filtered(lambda l: not l.display_type).action_reject_margin()

    def action_reset_all_margins(self):
        for order in self:
            order.order_line.filtered(lambda l: not l.display_type).action_reset_margin_approval()

    def _check_general_margin_not_negative(self):
        """Valida directamente el valor del campo `margin_percent` de la
        orden, antes de mover ninguna línea, sin depender de filtrados sobre
        order_line. Usa float_compare con precisión fija para evitar falsos
        positivos por residuos de punto flotante (ej. un margen de 19.9999%
        que en pantalla se ve como 20%). Se omite por completo si la orden
        tiene marcado `allow_zero_margin_confirmation`."""
        self.ensure_one()
        if self.allow_zero_margin_confirmation:
            return
        if float_compare(self.margin_percent, 0.20, precision_digits=4) <= 0:
            raise UserError(_(
                "No se puede confirmar la cotización: el margen general (%s%%) "
                "es igual o menor al 20%%."
            ) % round(self.margin_percent * 100, 2))

    def _check_margin_decisions_defined(self):
        """Toda línea decidible (no sección/nota) debe tener una decisión de
        margen explícita -aprobado o rechazado-, sin importar el signo del
        margen, antes de poder confirmar, enviar o imprimir la cotización.
        Se omite por completo si el margen general de la orden ya es mayor o
        igual al 35%: en ese caso no hace falta decisión línea por línea."""
        self.ensure_one()
        if float_compare(self.margin_percent, 0.35, precision_digits=4) >= 0:
            return
        pending_lines = self.order_line.filtered(
            lambda l: not l.display_type and l.margin_approval_status == 'pending'
        )
        if pending_lines:
            raise UserError(_(
                "No se puede continuar: existen líneas sin una decisión de "
                "margen definida (aprobado o rechazado)."
            ))

    def _split_rejected_margin_lines(self):
        """Extrae las líneas con margen rechazado a una nueva cotización con
        los mismos datos de cabecera, para que no formen parte de la orden
        que se está confirmando."""
        self.ensure_one()
        rejected_lines = self.order_line.filtered(
            lambda l: l.margin_approval_status == 'rejected'
        )
        if not rejected_lines:
            return self.env['sale.order']

        new_order = self.copy(default={'order_line': []})
        for line in rejected_lines:
            line.copy(default={'order_id': new_order.id})
        rejected_lines.unlink()

        self.message_post(body=Markup(_(
            "Se creó la cotización %s con las líneas de margen rechazado."
        )) % new_order._get_html_link())
        new_order.message_post(body=Markup(_(
            "Cotización creada a partir de las líneas de margen rechazado de %s."
        )) % self._get_html_link())

        return new_order

    def write(self, vals):
        result = super().write(vals)
        if 'contract_global_due_date' in vals:
            for order in self:
                order.order_line.write({'due_date': order.contract_global_due_date})
        return result

    def action_confirm(self):
        for order in self:
            order._check_margin_decisions_defined()
        for order in self:
            order._check_general_margin_not_negative()
        for order in self:
            order._split_rejected_margin_lines()
        return super().action_confirm()

    def action_quotation_send(self):
        for order in self:
            order._check_margin_decisions_defined()
        return super().action_quotation_send()

    def action_print_saleorder(self):
        for order in self:
            order._check_margin_decisions_defined()
        return self.env.ref('sale.action_report_saleorder').report_action(self.ids)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    due_date = fields.Date(
        string="Vencimiento",
    )
    margin_approval_status = fields.Selection(
        selection=[
            ('pending', 'Pendiente'),
            ('approved', 'Aprobado'),
            ('rejected', 'Rechazado'),
        ],
        string="Estado de Aprobación de Margen",
        default='pending',
        copy=False,
        readonly=True,
    )
    can_approve_sale_margin = fields.Boolean(
        string="Puede Aprobar Márgenes",
        compute='_compute_can_approve_sale_margin',
    )
    product_is_kit = fields.Boolean(
        string="Es Kit",
        compute='_compute_product_is_kit',
    )
    can_edit_price_unit = fields.Boolean(
        string="Puede Editar Precio Unitario",
        compute='_compute_can_edit_price_unit',
    )

    @api.depends_context('uid')
    def _compute_can_edit_price_unit(self):
        can_edit = self.env.user.can_edit_price_unit
        for line in self:
            line.can_edit_price_unit = can_edit

    @api.depends_context('bypass_product_updatable_check')
    def _compute_product_updatable(self):
        # Permite que flujos internos controlados (p. ej. el wizard "Cambiar
        # Producto") reemplacen el producto de una línea ya entregada o
        # facturada, evitando el bloqueo nativo de Odoo pensado solo para la
        # edición manual desde el formulario.
        super()._compute_product_updatable()
        if self.env.context.get('bypass_product_updatable_check'):
            self.product_updatable = True

    @api.depends('product_id.bom_count')
    def _compute_product_is_kit(self):
        # No se usa `product_id.is_kits` (evalúa product.template) porque acá
        # se necesita a nivel de variante (product.product); se detecta
        # cualquier BoM asociada al producto, sin filtrar por tipo.
        for line in self:
            line.product_is_kit = bool(line.product_id.bom_count)

    @api.depends_context('uid')
    def _compute_can_approve_sale_margin(self):
        can_approve = self.env.user.approve_sale_margins
        for line in self:
            line.can_approve_sale_margin = can_approve

    def _check_can_decide_margin(self):
        for line in self:
            if not line.can_approve_sale_margin:
                raise UserError(_("No tiene permisos para aprobar o rechazar márgenes de venta."))
            if line.state != 'draft':
                raise UserError(_("Solo se puede decidir sobre el margen de líneas en estado borrador."))

    def action_approve_margin(self):
        self._check_can_decide_margin()
        self.write({'margin_approval_status': 'approved'})
        self._log_margin_decision(_("aprobó"))

    def action_reject_margin(self):
        self._check_can_decide_margin()
        self.write({'margin_approval_status': 'rejected'})
        self._log_margin_decision(_("rechazó"))

    def action_reset_margin_approval(self):
        self._check_can_decide_margin()
        self.write({'margin_approval_status': 'pending'})
        self._log_margin_decision(_("restableció"))

    def _log_margin_decision(self, action_label):
        for line in self:
            body = Markup(_(
                "%(user)s %(action)s el margen de la línea <b>%(product)s</b>.",
                user=html_escape(self.env.user.display_name),
                action=action_label,
                product=html_escape(line.product_id.display_name or line.name or ''),
            ))
            line.order_id.message_post(body=body)

    @api.model
    def action_open_supplierinfo_for_product(self, product_id):
        product = self.env['product.product'].browse(product_id)
        return {
            'type': 'ir.actions.act_window',
            'name': _("Proveedores del Producto"),
            'res_model': 'product.supplierinfo',
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('sale_order_custom.view_product_supplierinfo_list_editable').id, 'list'),
                (False, 'form'),
            ],
            'domain': [
                '&', ('product_tmpl_id', '=', product.product_tmpl_id.id),
                '|', ('product_id', '=', False), ('product_id', '=', product.id),
            ],
            'context': {
                'default_product_id': product.id,
            },
        }

    @api.model
    def _get_kit_bom_for_product(self, product):
        return self.env['mrp.bom'].search([
            '|', ('product_id', '=', product.id),
            '&', ('product_id', '=', False), ('product_tmpl_id', '=', product.product_tmpl_id.id),
        ], order='id desc', limit=1)

    @api.model
    def action_view_kit_components(self, product_id):
        product = self.env['product.product'].browse(product_id)
        bom = self._get_kit_bom_for_product(product)
        if not bom:
            raise UserError(_("Este producto no tiene una lista de materiales de kit."))
        return {
            'type': 'ir.actions.act_window',
            'name': _("Componentes del Kit"),
            'res_model': 'mrp.bom',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'res_id': bom.id,
        }

    @api.model
    def action_view_kit_stock(self, product_id):
        product = self.env['product.product'].browse(product_id)
        bom = self._get_kit_bom_for_product(product)
        component_products = bom.bom_line_ids.product_id
        return {
            'type': 'ir.actions.act_window',
            'name': _("Existencias de los Componentes del Kit"),
            'res_model': 'stock.quant',
            'view_mode': 'list',
            'views': [(False, 'list')],
            'domain': [
                ('product_id', 'in', component_products.ids),
                ('location_id.usage', '=', 'internal'),
            ],
        }

    def action_open_add_kit_wizard(self):
        order_id = self.env.context.get('order_id')
        return {
            'type': 'ir.actions.act_window',
            'name': _("Agregar Kit"),
            'res_model': 'mrp.bom',
            'view_mode': 'form',
            'views': [(self.env.ref('sale_order_custom.mrp_bom_form_view_kit').id, 'form')],
            'target': 'new',
            'context': {
                'kit': True,
                'kit_sale_order_id': order_id,
                'default_type': 'phantom',
            },
        }

    _TRACKED_FIELD_LABELS = {
        'product_id': "Producto",
        'product_uom_qty': "Cantidad",
        'product_uom_id': "Unidad de Medida",
        'price_unit': "Precio Unitario",
        'discount': "Descuento (%)",
        'tax_ids': "Impuestos",
    }

    def _format_tracked_value(self, fname, value):
        field = self._fields[fname]
        if field.type == 'many2one':
            return html_escape(value.display_name) if value else _("Ninguno")
        if field.type == 'many2many':
            names = ', '.join(value.mapped('display_name'))
            return html_escape(names) if names else _("Ninguno")
        if field.type in ('float', 'monetary'):
            return '%.2f' % value
        if value is False or value is None or value == '':
            return _("Ninguno")
        return html_escape(str(value))

    def write(self, vals):
        tracked_fields = [f for f in self._TRACKED_FIELD_LABELS if f in vals]
        old_values = {}
        if tracked_fields and not self.env.context.get('sale_write_from_compute'):
            for line in self:
                if line.display_type or line.is_downpayment:
                    continue
                old_values[line.id] = {f: line[f] for f in tracked_fields}

        result = super().write(vals)

        for line in self:
            line_old_values = old_values.get(line.id)
            if not line_old_values:
                continue
            change_items = Markup('')
            for fname in tracked_fields:
                old_value = line_old_values[fname]
                new_value = line[fname]
                if old_value == new_value:
                    continue
                label = self._TRACKED_FIELD_LABELS[fname]
                change_items += Markup(
                    '<li><b>%s</b>: '
                    '<span style="color:#dc3545;text-decoration:line-through;">%s</span>'
                    ' <b>&#8594;</b> '
                    '<span style="color:#28a745;font-weight:bold;">%s</span></li>'
                ) % (
                    label,
                    line._format_tracked_value(fname, old_value),
                    line._format_tracked_value(fname, new_value),
                )
            if change_items:
                body = Markup(
                    '<div>%s <b style="color:#875a7b;">%s</b> %s <b>%s</b>:</div>'
                    '<ul style="margin-bottom:0;">%s</ul>'
                ) % (
                    _("Línea de venta"),
                    line.product_id.display_name or line.name or '',
                    _("modificada por"),
                    self.env.user.display_name,
                    change_items,
                )
                line.order_id.message_post(body=body)

        return result
