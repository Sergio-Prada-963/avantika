# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseOrderChangeProductWizard(models.TransientModel):
    _name = 'purchase.order.change.product.wizard'
    _description = 'Cambiar Producto de la Orden de Compra'

    order_id = fields.Many2one('purchase.order', required=True)
    purchase_line_id = fields.Many2one(
        'purchase.order.line',
        string="Producto a Cambiar",
        required=True,
        domain="[('order_id', '=', order_id), ('display_type', '=', False),"
               " ('is_downpayment', '=', False),"
               " ('qty_received', '=', 0), ('qty_invoiced', '=', 0)]",
    )
    current_product_id = fields.Many2one(
        related='purchase_line_id.product_id', string="Producto Actual", readonly=True,
    )
    new_product_id = fields.Many2one(
        'product.product', string="Nuevo Producto", required=True,
        domain="[('purchase_ok', '=', True)]",
    )
    keep_price = fields.Boolean(string="Conservar Precio", default=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'order_id' in fields_list and not res.get('order_id'):
            res['order_id'] = self.env.context.get('active_id')
        return res

    def _get_product_change_message(self, old_product, new_product, doc_label):
        template = _(
            "Se cambió el producto de %(old)s a %(new)s en %(doc)s, por un "
            "cambio de producto realizado desde la orden de compra %(purchase_order)s."
        )
        return Markup(template) % {
            'old': Markup(
                '<span style="color:#dc3545;text-decoration:line-through;">%s</span>'
            ) % old_product.display_name,
            'new': Markup(
                '<span style="color:#28a745;font-weight:bold;">%s</span>'
            ) % new_product.display_name,
            'doc': doc_label,
            'purchase_order': self.order_id.display_name,
        }

    def _change_sale_line(self, sale_line, old_product, new_product):
        if not sale_line or sale_line.order_id.state == 'cancel':
            return False
        old_price_unit = sale_line.price_unit
        # bypass_product_updatable_check evita el bloqueo nativo de Odoo para
        # líneas ya entregadas/facturadas (igual que el wizard equivalente
        # del lado de ventas); force_price_recomputation asegura que el
        # precio se recalcule aunque ya difiera de technical_price_unit.
        sale_line.with_context(
            bypass_product_updatable_check=True,
            force_price_recomputation=True,
        ).write({
            'product_id': new_product.id,
            'product_uom_id': new_product.uom_id.id,
        })
        if self.keep_price:
            sale_line.price_unit = old_price_unit
        sale_line.order_id.message_post(
            body=self._get_product_change_message(old_product, new_product, _("esta orden de venta"))
        )
        return True

    def _change_delivery_moves(self, moves, old_product, new_product):
        updatable = moves.filtered(lambda m: m.state not in ('done', 'cancel'))
        skipped = moves - updatable
        for move in updatable:
            move._do_unreserve()
            move.write({
                'product_id': new_product.id,
                'product_uom': new_product.uom_id.id,
            })
            move.move_line_ids.write({
                'product_id': new_product.id,
                'product_uom_id': new_product.uom_id.id,
            })
            if move.state in ('confirmed', 'waiting', 'partially_available'):
                move._action_assign()
        for picking in updatable.picking_id:
            picking.message_post(
                body=self._get_product_change_message(old_product, new_product, _("esta entrega"))
            )
        return updatable, skipped

    def action_change_product(self):
        self.ensure_one()
        line = self.purchase_line_id
        new_product = self.new_product_id
        if line.product_id == new_product:
            raise UserError(_("El producto seleccionado es el mismo que ya tiene la línea."))
        if line.order_id.state == 'cancel':
            raise UserError(_("No se puede cambiar el producto de una orden de compra cancelada."))
        if line.qty_received or line.qty_invoiced:
            raise UserError(_(
                "No se puede cambiar el producto: esta línea ya tiene "
                "cantidad recibida o facturada."
            ))

        old_product = line.product_id
        old_price_unit = line.price_unit
        sale_line = line.sale_line_id
        moves = sale_line.move_ids if sale_line else self.env['stock.move']

        name = new_product.display_name
        if new_product.description_purchase:
            name += '\n' + new_product.description_purchase
        line.write({
            'product_id': new_product.id,
            'product_uom_id': new_product.uom_id.id,
            'name': name,
        })
        if self.keep_price:
            line.price_unit = old_price_unit
        else:
            seller = new_product._select_seller(
                partner_id=line.order_id.partner_id,
                quantity=line.product_qty,
                uom_id=line.product_uom_id,
            )
            line.price_unit = seller.price if seller else new_product.standard_price

        changed_sale = self._change_sale_line(sale_line, old_product, new_product)
        updated_moves, skipped_moves = self._change_delivery_moves(moves, old_product, new_product)

        price_action = _("conservado") if self.keep_price else _("recalculado")
        old_html = Markup(
            '<span style="color:#dc3545;text-decoration:line-through;">%s</span>'
        ) % old_product.display_name
        new_html = Markup(
            '<span style="color:#28a745;font-weight:bold;">%s</span>'
        ) % new_product.display_name

        message = Markup(_(
            "Producto cambiado de %(old)s a %(new)s en la línea de compra "
            "(precio %(price_action)s)."
        )) % {
            'old': old_html,
            'new': new_html,
            'price_action': price_action,
        }
        if changed_sale:
            message += Markup('<br/>') + _("Se actualizó el producto en la línea de venta relacionada.")
        elif sale_line:
            message += Markup('<br/>') + _(
                "No se pudo actualizar la línea de venta relacionada (está cancelada)."
            )
        if updated_moves:
            message += Markup('<br/>') + Markup(_(
                "Se actualizó el producto en %(count)s movimiento(s) de entrega relacionado(s)."
            )) % {'count': len(updated_moves)}
        if skipped_moves:
            message += Markup('<br/>') + Markup(_(
                "No se pudo actualizar %(count)s movimiento(s) de entrega relacionado(s) "
                "(ya están hechos o cancelados)."
            )) % {'count': len(skipped_moves)}
        self.order_id.message_post(body=message)

        return {'type': 'ir.actions.act_window_close'}
