# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import html_escape


class SaleOrderChangeProductWizard(models.TransientModel):
    _name = 'sale.order.change.product.wizard'
    _description = 'Cambiar Producto de la Orden de Venta'

    order_id = fields.Many2one('sale.order', required=True)
    sale_line_id = fields.Many2one(
        'sale.order.line',
        string="Producto a Cambiar",
        required=True,
        domain="[('order_id', '=', order_id), ('display_type', '=', False), ('is_downpayment', '=', False)]",
    )
    current_product_id = fields.Many2one(
        related='sale_line_id.product_id', string="Producto Actual", readonly=True,
    )
    new_product_id = fields.Many2one(
        'product.product', string="Nuevo Producto", required=True,
        domain="[('sale_ok', '=', True)]",
    )
    keep_price = fields.Boolean(string="Conservar Precio", default=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'order_id' in fields_list and not res.get('order_id'):
            res['order_id'] = self.env.context.get('active_id')
        return res

    def _get_linked_purchase_lines(self, sale_line):
        """Encuentra las líneas de orden de compra generadas para abastecer
        esta línea de venta (ruta Comprar + Bajo Pedido). No existe una
        relación directa en este negocio entre sale.order.line y
        purchase.order.line, así que se llega por dos vías:
        - purchase.order.line.move_dest_ids: se llena desde que se crea la
          línea de compra (incluso si la orden de compra sigue en borrador
          y todavía no existe el movimiento de recepción).
        - la cadena move_orig_ids de los movimientos de entrega: respaldo
          para cuando move_dest_ids no quedó poblado por algún motivo."""
        moves = sale_line.move_ids
        if not moves:
            return self.env['purchase.order.line']

        PurchaseLine = self.env['purchase.order.line']
        purchase_lines = self.env['purchase.order.line']
        if 'move_dest_ids' in PurchaseLine._fields:
            purchase_lines |= PurchaseLine.search([('move_dest_ids', 'in', moves.ids)])

        if 'purchase_line_id' in moves._fields:
            seen = self.env['stock.move']
            to_visit = moves
            while to_visit:
                seen |= to_visit
                to_visit = to_visit.move_orig_ids - seen
            purchase_lines |= seen.mapped('purchase_line_id')

        return purchase_lines

    def _get_product_change_message(self, old_product, new_product, doc_label):
        return Markup(_(
            "Se cambió el producto de <b>%(old)s</b> a <b>%(new)s</b> en %(doc)s, "
            "por un cambio de producto realizado desde la orden de venta %(sale_order)s.",
            old=html_escape(old_product.display_name),
            new=html_escape(new_product.display_name),
            doc=doc_label,
            sale_order=html_escape(self.order_id.display_name),
        ))

    def _change_purchase_lines(self, purchase_lines, old_product, new_product):
        updatable = purchase_lines.filtered(
            lambda l: l.order_id.state != 'cancel'
            and not l.qty_received
            and not l.qty_invoiced
        )
        skipped = purchase_lines - updatable
        for purchase_line in updatable:
            name = new_product.display_name
            if new_product.description_purchase:
                name += '\n' + new_product.description_purchase
            purchase_line.write({
                'product_id': new_product.id,
                'product_uom_id': new_product.uom_id.id,
                'name': name,
            })
            if not self.keep_price:
                seller = new_product._select_seller(
                    partner_id=purchase_line.order_id.partner_id,
                    quantity=purchase_line.product_qty,
                    uom_id=purchase_line.product_uom_id,
                )
                purchase_line.price_unit = seller.price if seller else new_product.standard_price
        for order in updatable.order_id:
            order.message_post(
                body=self._get_product_change_message(old_product, new_product, _("esta orden de compra"))
            )
        return updatable, skipped

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
        line = self.sale_line_id
        new_product = self.new_product_id
        if line.product_id == new_product:
            raise UserError(_("El producto seleccionado es el mismo que ya tiene la línea."))

        old_product = line.product_id
        old_price_unit = line.price_unit
        purchase_lines = self._get_linked_purchase_lines(line)
        moves = line.move_ids

        # El producto de la línea de venta se cambia primero: stock.move.write
        # (en sale_stock) desvincula sale_line_id de un movimiento en cuanto
        # su product_id deja de coincidir con el de la línea de venta, así que
        # hay que igualar la línea de venta antes de tocar los movimientos.
        # force_price_recomputation es necesario porque, si el precio de la
        # línea ya difiere de technical_price_unit (por una edición manual
        # previa), Odoo la trata como "precio manual" y se salta el
        # recálculo automático al cambiar el producto.
        line.with_context(
            bypass_product_updatable_check=True,
            force_price_recomputation=True,
        ).write({
            'product_id': new_product.id,
            'product_uom_id': new_product.uom_id.id,
        })
        if self.keep_price:
            line.price_unit = old_price_unit

        updated_purchase, skipped_purchase = self._change_purchase_lines(purchase_lines, old_product, new_product)
        updated_moves, skipped_moves = self._change_delivery_moves(moves, old_product, new_product)

        message = _(
            "Producto cambiado de %(old)s a %(new)s en la línea de venta (precio %(price_action)s).",
            old=html_escape(old_product.display_name),
            new=html_escape(new_product.display_name),
            price_action=_("conservado") if self.keep_price else _("recalculado"),
        )
        if updated_purchase:
            message += "<br/>" + _(
                "Se actualizó el producto en %(count)s línea(s) de compra relacionada(s).",
                count=len(updated_purchase),
            )
        if skipped_purchase:
            message += "<br/>" + _(
                "No se pudo actualizar %(count)s línea(s) de compra relacionada(s) "
                "(ya tienen cantidad recibida o facturada, o están canceladas).",
                count=len(skipped_purchase),
            )
        if updated_moves:
            message += "<br/>" + _(
                "Se actualizó el producto en %(count)s movimiento(s) de entrega relacionado(s).",
                count=len(updated_moves),
            )
        if skipped_moves:
            message += "<br/>" + _(
                "No se pudo actualizar %(count)s movimiento(s) de entrega relacionado(s) "
                "(ya están hechos o cancelados).",
                count=len(skipped_moves),
            )
        self.order_id.message_post(body=Markup(message))

        return {'type': 'ir.actions.act_window_close'}
