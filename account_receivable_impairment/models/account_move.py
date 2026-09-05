# -*- coding: utf-8 -*-
from odoo import _, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    impairment_calculation_id = fields.Many2one(
        'account.receivable.impairment.calculation',
        compute='_compute_impairment_calculation_id',
        string='Cálculo de Deterioro',
    )
    impairment_invoice_ids = fields.Many2many(
        'account.move',
        relation='account_move_impairment_invoice_rel',
        column1='entry_move_id', column2='invoice_move_id',
        compute='_compute_impairment_calculation_id', string='Facturas',
    )
    impairment_invoice_count = fields.Integer(compute='_compute_impairment_calculation_id')
    impairment_calculation_line_ids = fields.One2many(
        'account.receivable.impairment.calculation.line', 'move_id',
        string='Líneas de Deterioro de Cartera',
    )

    def _compute_impairment_calculation_id(self):
        Calculation = self.env['account.receivable.impairment.calculation']
        for move in self:
            calculation = Calculation.search([('move_id', '=', move.id)], limit=1)
            move.impairment_calculation_id = calculation
            move.impairment_invoice_ids = calculation.line_ids.move_id
            move.impairment_invoice_count = len(move.impairment_invoice_ids)

    def action_view_impairment_invoices(self):
        self.ensure_one()
        invoices = self.impairment_invoice_ids
        action = {
            'name': _('Facturas del Cálculo de Deterioro'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
        }
        if len(invoices) == 1:
            action.update({'view_mode': 'form', 'res_id': invoices.id})
        else:
            action.update({'view_mode': 'list,form', 'domain': [('id', 'in', invoices.ids)]})
        return action
