# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    impairment_evaluate = fields.Boolean(
        string='Evaluar Deterioro de Cartera',
        help='Marca esta cuenta por cobrar para que sea evaluada en el '
             'cálculo de deterioro de cartera (NIIF 9). Si ninguna cuenta '
             'de la compañía está marcada, se evalúan todas las cuentas de '
             'tipo "A cobrar".',
    )
