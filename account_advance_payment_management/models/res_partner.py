from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    apm_advance_receivable_account_id = fields.Many2one(
        'account.account',
        string="Cuenta de Anticipos de Cliente",
        help="Cuenta de anticipo específica para este contacto. Si está "
             "configurada, se usará por defecto al registrar un anticipo "
             "de cliente para este contacto, en lugar de la cuenta de "
             "anticipos de clientes general de la compañía.",
    )
    apm_advance_payable_account_id = fields.Many2one(
        'account.account',
        string="Cuenta de Anticipos a Proveedor",
        help="Cuenta de anticipo específica para este contacto. Si está "
             "configurada, se usará por defecto al registrar un anticipo "
             "a proveedor para este contacto, en lugar de la cuenta de "
             "anticipos a proveedores general de la compañía.",
    )
