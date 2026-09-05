# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    impairment_periodicity = fields.Selection(
        related='company_id.impairment_periodicity', readonly=False,
        string='Periodicidad de Cálculo Automático')
    impairment_journal_id = fields.Many2one(
        related='company_id.impairment_journal_id', readonly=False,
        string='Diario')
    impairment_expense_account_id = fields.Many2one(
        related='company_id.impairment_expense_account_id', readonly=False,
        string='Cuenta de gasto')
    impairment_provision_account_id = fields.Many2one(
        related='company_id.impairment_provision_account_id', readonly=False,
        string='Cuenta de provisión')
    impairment_line_ids = fields.One2many(
        related='company_id.impairment_line_ids', readonly=False,
        string='Rangos de mora')
