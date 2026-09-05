# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    dynamic_line_ids = fields.One2many('account.payment.dynamic.line', 'payment_id')

    def _prepare_move_counterpart_lines(self, default_values):
        # EXTENDS account: cuando el pago viene de un registro de pago
        # agrupado (varias facturas del mismo tercero), se reparte la
        # contrapartida en una línea por factura en vez de una sola línea con
        # el total combinado.
        self.ensure_one()
        lines = self.dynamic_line_ids.filtered(lambda l: l.kind == 'counterpart')
        if not lines:
            return super()._prepare_move_counterpart_lines(default_values)
        return [line._to_move_line_vals(default_values['name']) for line in lines]

    def _prepare_move_withholding_lines(self, default_values):
        # EXTENDS account: agrega una línea de retención por cada impuesto
        # que se sumó dinámicamente desde el registro de pago multifactura
        # (sin modificar la factura original).
        self.ensure_one()
        lines = super()._prepare_move_withholding_lines(default_values)
        dynamic_lines = self.dynamic_line_ids.filtered(lambda l: l.kind == 'withholding')
        return lines + [line._to_move_line_vals(line.name) for line in dynamic_lines]
