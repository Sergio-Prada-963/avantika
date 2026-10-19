# -*- coding: utf-8 -*-
from odoo import api, fields, models

ORDER_LINE_TRIGGER_FIELDS = (
    'order_line',
)
# A7
ORDER_TRIGGER_FIELDS = {
    'order_line', 'partner_id', 'currency_id', 'fiscal_position_id',
    'picking_type_id', 'wbt_service_city_id', 'date_order',
}


class PurchaseOrder(models.Model):
    _name = 'purchase.order'
    _inherit = ['purchase.order', 'wbt.withholding.mixin']

    wbt_service_city_id = fields.Many2one(
        'res.city',
        string='Ciudad del servicio (ReteICA)',
        help="Ciudad donde se presta el servicio comprado. Si está vacía, los "
             "servicios usan la ciudad de la bodega que recibe. Los bienes "
             "siempre usan la ciudad de la bodega que recibe.",
    )

    @api.onchange(*ORDER_LINE_TRIGGER_FIELDS, 'fiscal_position_id', 'partner_id',
                  'picking_type_id', 'wbt_service_city_id', 'date_order', 'currency_id')
    def _onchange_sync_uvt_withholding_taxes(self):
        self._wbt_sync_withholding_taxes()

    @api.model_create_multi
    def create(self, vals_list):
        # purchase.order.fiscal_position_id no es computado guardado: el núcleo
        # solo lo llena con un onchange de partner_id que no corre al crear
        # por código.
        for vals in vals_list:
            if vals.get('partner_id') and not vals.get('fiscal_position_id'):
                partner = self.env['res.partner'].browse(vals['partner_id'])
                vals['fiscal_position_id'] = self.env['account.fiscal.position']._get_fiscal_position(partner).id
        orders = super().create(vals_list)
        orders._wbt_sync_withholding_taxes()
        return orders

    def write(self, vals):
        res = super().write(vals)
        if ORDER_TRIGGER_FIELDS & set(vals):
            self._wbt_sync_withholding_taxes()
        return res

    def button_confirm(self):
        # Respaldo final antes de confirmar.
        self._wbt_sync_withholding_taxes()
        return super().button_confirm()

    # ------------------------------------------------------------------
    # Implementación del mixin
    # ------------------------------------------------------------------
    def _wbt_type_tax_use(self):
        return 'purchase'

    def _wbt_is_editable(self):
        # A9: ni bloqueadas, ni canceladas, ni ya facturadas
        self.ensure_one()
        return (
            self.state != 'cancel'
            and not self.locked
            and not self.order_line._origin.invoice_lines
        )

    def _wbt_lines(self):
        return self.order_line.filtered(lambda l: not l.display_type)

    def _wbt_lines_field(self):
        return 'order_line'

    def _wbt_date(self):
        return self.date_order or fields.Date.context_today(self)

    def _wbt_line_city(self, line, kind):
        # A4 compras: bienes -> bodega que recibe; servicios -> ciudad del encabezado
        warehouse_city = self.picking_type_id.warehouse_id.partner_id.city_id
        if kind == 'service':
            return self.wbt_service_city_id or warehouse_city
        if kind == 'goods':
            return warehouse_city
        return self.env['res.city']


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

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
