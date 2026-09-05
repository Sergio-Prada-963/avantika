from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    apm_advance_receivable_account_id = fields.Many2one(
        related='company_id.apm_advance_receivable_account_id', readonly=False)
    apm_advance_payable_account_id = fields.Many2one(
        related='company_id.apm_advance_payable_account_id', readonly=False)
    apm_advance_journal_customer_id = fields.Many2one(
        related='company_id.apm_advance_journal_customer_id', readonly=False)
    apm_advance_journal_supplier_id = fields.Many2one(
        related='company_id.apm_advance_journal_supplier_id', readonly=False)
