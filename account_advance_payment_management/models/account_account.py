from odoo import api, fields, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    apm_advance_account = fields.Boolean(
        string="Usada para Anticipos",
        help="Los apuntes contables registrados en esta cuenta se consideran "
             "anticipos de clientes/proveedores y se ofrecerán para su "
             "legalización automática contra facturas futuras.",
    )

    @api.onchange('apm_advance_account')
    def _onchange_apm_advance_account(self):
        if self.apm_advance_account:
            self.reconcile = True

    def write(self, vals):
        if vals.get('apm_advance_account'):
            vals['reconcile'] = True
        return super().write(vals)
