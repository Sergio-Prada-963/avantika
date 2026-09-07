# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    delivery_date = fields.Date(
        string="Fecha de Entrega de Bienes",
        copy=False,
    )
    qr_code = fields.Binary(
        string="Código QR",
        copy=False,
        attachment=False,
        help="Imagen del código QR de validación de la factura electrónica.",
    )
    cufe = fields.Char(
        string="CUFE",
        copy=False,
        help="Código Único de Facturación Electrónica asignado por la DIAN.",
    )
    dian_validation_date = fields.Datetime(
        string="Fecha Validación DIAN",
        copy=False,
    )
