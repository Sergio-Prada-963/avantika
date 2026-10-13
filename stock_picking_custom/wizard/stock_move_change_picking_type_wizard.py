# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockMoveChangePickingTypeWizard(models.TransientModel):
    _name = 'stock.move.change.picking.type.wizard'
    _description = "Cambiar Tipo de Operación de Movimientos"

    move_ids = fields.Many2many('stock.move', string="Movimientos")
    company_id = fields.Many2one(
        'res.company', string="Compañía",
        default=lambda self: self.env.company,
    )
    picking_type_id = fields.Many2one(
        'stock.picking.type',
        string="Nuevo Tipo de Operación",
        required=True,
        help="Mismo dominio que el campo 'Tipo de Operación' en la "
             "transferencia (stock.picking): solo tipos de código "
             "entrada/salida/interno, de la compañía actual o sin "
             "compañía asignada.",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'move_ids' in fields_list:
            res['move_ids'] = [(6, 0, self.env.context.get('active_ids', []))]
        return res

    def action_change_picking_type(self):
        self.ensure_one()
        if not self.move_ids:
            raise UserError(_("Selecciona al menos un movimiento."))
        pickings = self.move_ids.picking_id
        if not pickings:
            raise UserError(_(
                "Ninguno de los movimientos seleccionados tiene una "
                "transferencia (stock.picking) asociada."
            ))
        pickings.write({'picking_type_id': self.picking_type_id.id})
