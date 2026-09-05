# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class AccountReceivableImpairmentMatrixLine(models.Model):
    _name = 'account.receivable.impairment.matrix.line'
    _description = 'Rango de Mora de Deterioro de Cartera'
    _order = 'day_from'

    company_id = fields.Many2one(
        'res.company', string='Compañía',
        required=True, ondelete='cascade', default=lambda self: self.env.company)
    sequence = fields.Integer(string='Secuencia', default=10)
    day_from = fields.Integer(string='Día desde', required=True)
    day_to = fields.Integer(
        string='Día hasta',
        help='Vacío o 0 significa "en adelante" (sin límite superior).')
    percentage = fields.Float(string='% Pérdida esperada', required=True, digits=0)
    name = fields.Char(string='Rango', compute='_compute_name')

    @api.depends('day_from', 'day_to')
    def _compute_name(self):
        for line in self:
            if line.day_to:
                line.name = _('%s - %s días', line.day_from, line.day_to)
            else:
                line.name = _('%s días en adelante', line.day_from)
