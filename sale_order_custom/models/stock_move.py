# -*- coding: utf-8 -*-
from odoo import api, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model_create_multi
    def create(self, vals_list):
        # Si la línea de venta ya tiene una ubicación de origen elegida,
        # el movimiento que se genera para cumplirla debe nacer con esa
        # misma ubicación (en vez de la que hubiera calculado la regla de
        # stock por defecto). Se excluyen los movimientos encadenados
        # (multi-etapa: recolección/empaque/entrega), que deben tomar la
        # ubicación de salida del paso anterior, no la de la línea.
        for vals in vals_list:
            sale_line_id = vals.get('sale_line_id')
            if not sale_line_id or vals.get('move_orig_ids'):
                continue
            line = self.env['sale.order.line'].browse(sale_line_id)
            if line.location_id:
                vals['location_id'] = line.location_id.id

        moves = super().create(vals_list)

        # Si, al revés, la línea todavía no tenía ubicación (no se pudo
        # sugerir una con existencias), se completa con la que terminó
        # usando el movimiento recién creado, para que ambos queden
        # sincronizados.
        for move in moves:
            if (
                move.sale_line_id
                and not move.sale_line_id.location_id
                and move.location_id
                and not move.move_orig_ids
            ):
                move.sale_line_id.location_id = move.location_id
        return moves

    def write(self, vals):
        res = super().write(vals)
        if 'location_id' in vals:
            for move in self:
                if (
                    move.sale_line_id
                    and not move.move_orig_ids
                    and move.sale_line_id.location_id != move.location_id
                ):
                    move.sale_line_id.location_id = move.location_id
        return res
