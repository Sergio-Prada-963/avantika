# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    secondary_account_id = fields.Many2one(
        'account.account', string="Cuenta Espejo (Libro Secundario)",
        company_dependent=False,
        domain="[('company_ids', 'in', company_ids), ('id', '!=', id)]",
        help="Cuenta contable equivalente a usar en el libro secundario "
             "(ej. Fiscal) cuando se replique un movimiento registrado en "
             "esta cuenta. Si se deja vacía, el motor de réplica usa la "
             "misma cuenta en ambos libros.",
    )
