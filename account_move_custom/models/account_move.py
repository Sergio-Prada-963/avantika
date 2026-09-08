# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    delivery_date = fields.Date(
        string="Fecha de Entrega de Bienes",
        copy=False,
    )
    dian_validation_date = fields.Datetime(
        string="Fecha Validación DIAN",
        copy=False,
    )
