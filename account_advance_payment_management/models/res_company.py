from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    apm_advance_receivable_account_id = fields.Many2one(
        'account.account',
        string="Cuenta de Anticipos de Clientes",
        help="Cuenta de pasivo por defecto para contabilizar los cobros "
             "anticipados de clientes que aún no tienen factura.",
    )
    apm_advance_payable_account_id = fields.Many2one(
        'account.account',
        string="Cuenta de Anticipos a Proveedores",
        help="Cuenta de activo por defecto para contabilizar los pagos "
             "anticipados a proveedores que aún no tienen factura.",
    )
    apm_advance_journal_customer_id = fields.Many2one(
        'account.journal',
        string="Diario de Anticipos de Clientes",
        help="Diario usado para los anticipos de clientes: tanto el pago del "
             "anticipo como el asiento de legalización que lo aplica contra "
             "una factura.",
    )
    apm_advance_journal_supplier_id = fields.Many2one(
        'account.journal',
        string="Diario de Anticipos a Proveedores",
        help="Diario usado para los anticipos a proveedores: tanto el pago "
             "del anticipo como el asiento de legalización que lo aplica "
             "contra una factura.",
    )
