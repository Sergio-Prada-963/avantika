# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockMoveCreateInternalTransferWizard(models.TransientModel):
    _name = 'stock.move.create.internal.transfer.wizard'
    _description = "Crear Traslado Interno desde Movimientos Pendientes"

    move_ids = fields.Many2many('stock.move', string="Movimientos")
    company_id = fields.Many2one(
        'res.company', string="Compañía",
        default=lambda self: self.env.company,
    )
    picking_type_id = fields.Many2one(
        'stock.picking.type',
        string="Tipo de Movimiento (Bodega Origen)",
        required=True,
        help="El traslado interno se crea con origen la bodega de este "
             "tipo de operación, y destino la bodega que ya tienen de "
             "origen los movimientos seleccionados.",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'move_ids' in fields_list:
            move_ids = self.env.context.get('active_ids', [])
            res['move_ids'] = [(6, 0, move_ids)]
        return res

    def _get_destination_warehouse(self):
        self.ensure_one()
        if not self.move_ids:
            raise UserError(_("Selecciona al menos un movimiento."))
        warehouses = self.move_ids.picking_id.picking_type_id.warehouse_id
        if len(warehouses) > 1:
            raise UserError(_(
                "Los movimientos seleccionados no tienen todos la misma "
                "bodega de origen (%s). Selecciona movimientos de una sola "
                "bodega."
            ) % ', '.join(warehouses.mapped('name')))
        if not warehouses:
            raise UserError(_(
                "No se pudo determinar la bodega de origen de los "
                "movimientos seleccionados."
            ))
        return warehouses

    def action_create_internal_transfer(self):
        self.ensure_one()
        dest_warehouse = self._get_destination_warehouse()
        source_warehouse = self.picking_type_id.warehouse_id
        if not source_warehouse:
            raise UserError(_(
                "El tipo de operación seleccionado no tiene una bodega "
                "asignada."
            ))
        if source_warehouse == dest_warehouse:
            raise UserError(_(
                "La bodega origen del tipo de operación seleccionado es la "
                "misma que la bodega destino de los movimientos "
                "seleccionados."
            ))

        # Solo se trae lo que todavía falta por cubrir (demanda - lo que ya
        # está reservado/cumplido en cada movimiento), nunca la demanda
        # completa: si parte ya está reservada, esa parte no debe volver a
        # pedirse. Y nunca más de lo que realmente hay libre en la bodega
        # origen elegida: si no alcanza, se trae solo lo que alcance.
        needed_by_product = defaultdict(float)
        for move in self.move_ids:
            missing = move.product_uom_qty - move.quantity
            if missing > 0:
                needed_by_product[move.product_id] += missing

        move_vals = []
        for product, needed in needed_by_product.items():
            available = product.with_context(warehouse_id=source_warehouse.id).free_qty
            qty = min(needed, available)
            if qty <= 0:
                continue
            move_vals.append((0, 0, {
                'product_id': product.id,
                'product_uom_qty': qty,
                'product_uom': product.uom_id.id,
                'location_id': source_warehouse.lot_stock_id.id,
                'location_dest_id': dest_warehouse.lot_stock_id.id,
            }))

        if not move_vals:
            raise UserError(_(
                "No hay nada que trasladar: la demanda de los movimientos "
                "seleccionados ya está cubierta, o no hay existencias "
                "disponibles en la bodega de origen elegida."
            ))

        picking = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id.id,
            'location_id': source_warehouse.lot_stock_id.id,
            'location_dest_id': dest_warehouse.lot_stock_id.id,
            'move_ids': move_vals,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _("Traslado Interno Creado"),
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': picking.id,
        }
