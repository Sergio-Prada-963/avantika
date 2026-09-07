# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    purchase_line_ids = fields.One2many(
        'purchase.order.line', 'sale_line_id',
        string="Líneas de Compra",
    )
    purchase_proveedor_id = fields.Many2one(
        'res.partner',
        string="Proveedor de Compra",
        related='pricelist_line_id.proveedor_id',
        store=True,
    )
    purchase_currency_id = fields.Many2one(
        'res.currency',
        string="Moneda Proveedor",
        compute='_compute_purchase_currency_id',
    )
    product_qty_available = fields.Float(
        string="Cantidad Disponible en Inventario",
        related='product_id.qty_available',
    )
    qty_reserved_delivery = fields.Float(
        string="Cantidad Reservada para el Pedido",
        compute='_compute_qty_reserved_delivery',
        store=True,
        digits='Product Unit',
    )
    qty_purchased = fields.Float(
        string="Cantidad Comprada",
        compute='_compute_qty_purchased',
        store=True,
        digits='Product Unit',
    )
    qty_to_purchase = fields.Float(
        string="Cantidad a Comprar",
        compute='_compute_qty_to_purchase',
        store=True,
        digits='Product Unit',
    )

    @api.depends('purchase_proveedor_id', 'product_id.seller_ids.partner_id', 'product_id.seller_ids.currency_id')
    def _compute_purchase_currency_id(self):
        for line in self:
            seller = line.product_id.seller_ids.filtered(
                lambda s: s.partner_id == line.purchase_proveedor_id
            )[:1]
            line.purchase_currency_id = seller.currency_id

    @api.depends(
        'move_ids.state',
        'move_ids.picked',
        'move_ids.picking_code',
        'move_ids.quantity',
    )
    def _compute_qty_reserved_delivery(self):
        for line in self:
            moves = line.move_ids.filtered(
                lambda m: m.picking_code == 'outgoing'
                and m.state in ('assigned', 'partially_available')
                and not m.picked
            )
            line.qty_reserved_delivery = sum(moves.mapped('quantity'))

    @api.depends(
        'purchase_line_ids.product_qty',
        'purchase_line_ids.order_id.state',
    )
    def _compute_qty_purchased(self):
        for line in self:
            confirmed_lines = line.purchase_line_ids.filtered(
                lambda l: l.order_id.state in ('purchase', 'done')
            )
            line.qty_purchased = sum(confirmed_lines.mapped('product_qty'))

    @api.depends('product_uom_qty', 'qty_reserved_delivery')
    def _compute_qty_to_purchase(self):
        for line in self:
            line.qty_to_purchase = max(line.product_uom_qty - line.qty_reserved_delivery, 0.0)

    def action_create_purchase_orders(self):
        lines = self.filtered(
            lambda l: not l.display_type and not l.is_downpayment and l.qty_to_purchase > 0
        )
        if not lines:
            raise UserError(_(
                "Selecciona al menos una línea de venta con cantidad "
                "pendiente por comprar."
            ))

        missing_provider = lines.filtered(lambda l: not l.purchase_proveedor_id)
        if missing_provider:
            raise UserError(_(
                "Las siguientes líneas no tienen un proveedor definido en su "
                "línea de lista de precios; no se puede generar la compra: %s"
            ) % ', '.join(missing_provider.mapped(lambda l: l.product_id.display_name or l.name)))

        groups = defaultdict(lambda: self.env['sale.order.line'])
        for line in lines:
            groups[line.purchase_proveedor_id] |= line

        purchase_orders = self.env['purchase.order']
        for proveedor, group_lines in groups.items():
            purchase_order = self.env['purchase.order'].create({
                'partner_id': proveedor.id,
                'order_line': [
                    (0, 0, {
                        'product_id': line.product_id.id,
                        'product_qty': line.qty_to_purchase,
                        'product_uom_id': line.product_uom_id.id,
                        'sale_line_id': line.id,
                    })
                    for line in group_lines
                ],
            })
            purchase_orders |= purchase_order

        return {
            'type': 'ir.actions.act_window',
            'name': _("Órdenes de Compra Creadas"),
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', purchase_orders.ids)],
        }
