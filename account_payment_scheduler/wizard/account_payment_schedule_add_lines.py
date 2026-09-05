# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountPaymentScheduleAddLines(models.TransientModel):
    _name = 'account.payment.schedule.add.lines'
    _description = "Agregar Facturas a la Programación de Pago"

    schedule_id = fields.Many2one(
        'account.payment.schedule', required=True, ondelete='cascade')
    move_ids = fields.Many2many(
        'account.move', string="Facturas",
        domain="[('move_type', 'in', ('in_invoice', 'in_refund')), "
               "('state', '=', 'posted'), "
               "('payment_state', 'in', ('not_paid', 'partial')), "
               "('company_id', '=', company_id)]")
    company_id = fields.Many2one(related='schedule_id.company_id')

    @api.onchange('schedule_id')
    def _onchange_schedule_id(self):
        for wizard in self:
            existing = wizard.schedule_id.line_ids.move_id
            if existing:
                wizard.move_ids = [(6, 0, wizard.move_ids.ids)]

    def action_add(self):
        self.ensure_one()
        existing_moves = self.schedule_id.line_ids.move_id
        new_moves = self.move_ids - existing_moves
        self.env['account.payment.schedule.line'].create([{
            'schedule_id': self.schedule_id.id,
            'move_id': move.id,
            'amount_to_pay': move.amount_residual,
        } for move in new_moves])
        return {'type': 'ir.actions.act_window_close'}
