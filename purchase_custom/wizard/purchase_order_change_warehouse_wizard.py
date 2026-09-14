# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseOrderChangeWarehouseWizard(models.TransientModel):
    _name = 'purchase.order.change.warehouse.wizard'
    _description = 'Cambiar Bodega de la Orden de Compra'

    order_id = fields.Many2one('purchase.order', required=True)
    current_picking_type_id = fields.Many2one(
        related='order_id.picking_type_id', string="Bodega Actual", readonly=True,
    )
    new_picking_type_id = fields.Many2one(
        'stock.picking.type',
        string="Nueva Bodega",
        required=True,
        domain="[('code', '=', 'incoming'),"
               " '|', ('warehouse_id', '=', False), ('warehouse_id.company_id', '=', company_id)]",
    )
    company_id = fields.Many2one(related='order_id.company_id', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'order_id' in fields_list and not res.get('order_id'):
            res['order_id'] = self.env.context.get('active_id')
        return res

    def _get_warehouse_change_message(self, old_warehouse, new_warehouse):
        template = _(
            "Se cambió la bodega de destino de %(old)s a %(new)s en la orden de compra %(purchase_order)s."
        )
        return Markup(template) % {
            'old': Markup(
                '<span style="color:#dc3545;text-decoration:line-through;">%s</span>'
            ) % (old_warehouse.display_name or _("Ninguna")),
            'new': Markup(
                '<span style="color:#28a745;font-weight:bold;">%s</span>'
            ) % new_warehouse.display_name,
            'purchase_order': self.order_id.display_name,
        }

    def action_change_warehouse(self):
        self.ensure_one()
        order = self.order_id
        new_type = self.new_picking_type_id
        if new_type == order.picking_type_id:
            raise UserError(_("El tipo de operación seleccionado es el mismo que ya tiene la orden."))
        if order.state == 'cancel':
            raise UserError(_("No se puede cambiar la bodega de una orden de compra cancelada."))

        old_warehouse = order.picking_type_id.warehouse_id
        new_warehouse = new_type.warehouse_id

        order.picking_type_id = new_type.id
        new_location_dest = order._get_destination_location()

        pickings = order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
        for picking in pickings:
            moves = picking.move_ids.filtered(lambda m: m.state not in ('done', 'cancel'))
            reserved_moves = moves.filtered(lambda m: m.state in ('assigned', 'partially_available'))
            reserved_moves._do_unreserve()

            picking.write({
                'picking_type_id': new_type.id,
                'location_dest_id': new_location_dest,
            })
            moves.write({
                'picking_type_id': new_type.id,
                'location_dest_id': new_location_dest,
                'warehouse_id': new_type.warehouse_id.id,
            })
            moves.move_line_ids.write({'location_dest_id': new_location_dest})

            if reserved_moves:
                reserved_moves._action_assign()

            picking.message_post(body=self._get_warehouse_change_message(old_warehouse, new_warehouse))

        order.message_post(body=self._get_warehouse_change_message(old_warehouse, new_warehouse))
        return {'type': 'ir.actions.act_window_close'}
