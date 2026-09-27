# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    indicador_verde = fields.Integer(
        string="Indicador Verde (días)",
        default=3,
        help="Límite de días de diferencia entre la fecha de la orden de "
             "venta y hoy para mostrar el indicador en verde. Rango: de 0 "
             "hasta este valor.",
    )
    indicador_amarillo = fields.Integer(
        string="Indicador Amarillo (días)",
        default=10,
        help="Límite de días para el indicador amarillo. Rango: desde "
             "(Indicador Verde + 1) hasta este valor.",
    )
    indicador_rojo = fields.Integer(
        string="Indicador Rojo (días)",
        default=18,
        help="Límite de días para el indicador rojo. Rango: desde "
             "(Indicador Amarillo + 1) hasta este valor.",
    )
    indicador_negro = fields.Integer(
        string="Indicador Negro (días)",
        default=25,
        help="Límite de días para el indicador negro. Rango: desde "
             "(Indicador Rojo + 1) en adelante (sin límite superior).",
    )
