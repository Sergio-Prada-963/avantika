# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payment_schedule_id = fields.Many2one(
        'account.payment.schedule',
        string="Programación de Pago",
        copy=False,
        help="Programación de pago desde la cual se generó este pago, si "
             "aplica.",
    )
