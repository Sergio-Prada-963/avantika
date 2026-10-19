# -*- coding: utf-8 -*-
from odoo import api, fields, models

INVOICE_LINE_TRIGGER_FIELDS = (
    'invoice_line_ids',
)
# A7: campos del encabezado que deciden las retenciones
MOVE_TRIGGER_FIELDS = {
    'invoice_line_ids', 'line_ids', 'partner_id', 'currency_id',
    'city_declaration_id', 'fiscal_position_id', 'partner_shipping_id',
    'invoice_date',
}
MOVE_TYPE_TAX_USE = {
    'out_invoice': 'sale',
    'out_refund': 'sale',
    'out_receipt': 'sale',
    'in_invoice': 'purchase',
    'in_refund': 'purchase',
    'in_receipt': 'purchase',
}


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'wbt.withholding.mixin']

    city_declaration_id = fields.Many2one(
        'res.city',
        string='Forzar ciudad ReteICA',
        copy=False,
        help="Vacío por defecto: la ciudad del ReteICA se toma línea por línea "
             "(bienes: bodega de salida/recepción; servicios: dirección de "
             "entrega en ventas o ciudad del servicio en compras). Si se llena, "
             "manda sobre todas las líneas.",
    )

    @api.onchange(*INVOICE_LINE_TRIGGER_FIELDS, 'city_declaration_id', 'fiscal_position_id',
                  'partner_id', 'partner_shipping_id', 'invoice_date', 'currency_id')
    def _onchange_sync_uvt_withholding_taxes(self):
        self._wbt_sync_withholding_taxes()

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        moves._wbt_sync_withholding_taxes()
        return moves

    def write(self, vals):
        res = super().write(vals)
        if MOVE_TRIGGER_FIELDS & set(vals):
            self._wbt_sync_withholding_taxes()
        return res

    def _post(self, soft=True):
        # Respaldo final antes de contabilizar.
        self._wbt_sync_withholding_taxes()
        return super()._post(soft=soft)

    # ------------------------------------------------------------------
    # Implementación del mixin
    # ------------------------------------------------------------------
    def _wbt_type_tax_use(self):
        return MOVE_TYPE_TAX_USE.get(self.move_type)

    def _wbt_is_editable(self):
        self.ensure_one()
        return (
            self.state == 'draft'
            and bool(self._wbt_type_tax_use())
            and not self.reversed_entry_id  # A8: notas crédito conservan las retenciones originales
        )

    def _wbt_lines(self):
        # A6: sin secciones ni notas
        return self.invoice_line_ids.filtered(lambda l: l.display_type == 'product')

    def _wbt_lines_field(self):
        return 'invoice_line_ids'

    def _wbt_date(self):
        return self.invoice_date or self.date or fields.Date.context_today(self)

    def _wbt_line_city(self, line, kind):
        City = self.env['res.city']
        if self.city_declaration_id:
            return self.city_declaration_id
        if not kind:
            return City
        if self._wbt_type_tax_use() == 'sale':
            if kind == 'service':
                return (self.partner_shipping_id or self.partner_id).city_id
            orders = line.sale_line_ids.order_id
            return orders[:1].warehouse_id.partner_id.city_id if orders else City
        # Compras
        order = line.purchase_line_id.order_id
        if not order:
            return City
        warehouse_city = order.picking_type_id.warehouse_id.partner_id.city_id
        if kind == 'service':
            return order.wbt_service_city_id or warehouse_city
        return warehouse_city


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('wbt_skip_sync'):
            moves = self.filtered(lambda l: l.display_type == 'product').move_id
            if moves:
                moves._wbt_sync_from_lines(self.filtered(lambda l: l.display_type == 'product'), vals)
        return res
