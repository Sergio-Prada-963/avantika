# -*- coding: utf-8 -*-
from odoo import api, fields, models

ORDER_LINE_TRIGGER_FIELDS = (
    'order_line',
)
# A7
ORDER_TRIGGER_FIELDS = {
    'order_line', 'partner_id', 'currency_id', 'pricelist_id', 'city_declaration_id',
    'fiscal_position_id', 'partner_shipping_id', 'warehouse_id', 'date_order',
}


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'wbt.withholding.mixin']

    city_declaration_id = fields.Many2one(
        'res.city',
        string='Forzar ciudad ReteICA',
        copy=False,
        help="Vacío por defecto: bienes toman la ciudad de la bodega de salida "
             "y servicios la de la dirección de entrega. Si se llena, manda "
             "sobre todas las líneas y pasa a la factura.",
    )

    @api.onchange(*ORDER_LINE_TRIGGER_FIELDS, 'city_declaration_id', 'fiscal_position_id',
                  'partner_id', 'partner_shipping_id', 'warehouse_id', 'date_order')
    def _onchange_sync_uvt_withholding_taxes(self):
        self._wbt_sync_withholding_taxes()

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders._wbt_sync_withholding_taxes()
        return orders

    def write(self, vals):
        res = super().write(vals)
        if ORDER_TRIGGER_FIELDS & set(vals):
            self._wbt_sync_withholding_taxes()
        return res

    def action_confirm(self):
        # Respaldo final antes de confirmar.
        self._wbt_sync_withholding_taxes()
        return super().action_confirm()

    def _prepare_invoice(self):
        values = super()._prepare_invoice()
        values['city_declaration_id'] = self.city_declaration_id.id
        return values

    # ------------------------------------------------------------------
    # Implementación del mixin
    # ------------------------------------------------------------------
    def _wbt_type_tax_use(self):
        return 'sale'

    def _wbt_is_editable(self):
        # A9: ni bloqueadas, ni canceladas, ni ya facturadas
        self.ensure_one()
        return (
            self.state != 'cancel'
            and not self.locked
            and not self.order_line._origin.invoice_lines
        )

    def _wbt_lines(self):
        return self.order_line.filtered(lambda l: not l.display_type and not l.is_downpayment)

    def _wbt_lines_field(self):
        return 'order_line'

    def _wbt_date(self):
        return self.date_order or fields.Date.context_today(self)

    def _wbt_line_city(self, line, kind):
        if self.city_declaration_id:
            return self.city_declaration_id
        if kind == 'service':
            return (self.partner_shipping_id or self.partner_id).city_id
        if kind == 'goods':
            return self.warehouse_id.partner_id.city_id
        return self.env['res.city']


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        if lines:
            lines.order_id._wbt_sync_from_lines(lines)
        return lines

    def write(self, vals):
        res = super().write(vals)
        if self:
            self.order_id._wbt_sync_from_lines(self, vals)
        return res
