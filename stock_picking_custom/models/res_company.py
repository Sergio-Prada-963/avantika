# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    stock_move_indicador_verde = fields.Integer(
        string="Indicador Verde (días de atraso)",
        default=0,
        help="Límite de días de atraso respecto a la fecha límite para "
             "mostrar el indicador en verde, en 'Movimientos Pendientes'. "
             "Rango: hasta este valor (los valores negativos, es decir "
             "fecha límite futura, siempre caen aquí).",
    )
    stock_move_indicador_amarillo = fields.Integer(
        string="Indicador Amarillo (días de atraso)",
        default=3,
        help="Límite de días de atraso para el indicador amarillo. Rango: "
             "desde (Indicador Verde + 1) hasta este valor.",
    )
    stock_move_indicador_rojo = fields.Integer(
        string="Indicador Rojo (días de atraso)",
        default=7,
        help="Límite de días de atraso para el indicador rojo. Rango: "
             "desde (Indicador Amarillo + 1) hasta este valor.",
    )
    stock_move_indicador_negro = fields.Integer(
        string="Indicador Negro (días de atraso)",
        default=15,
        help="Límite de días de atraso para el indicador negro. Rango: "
             "desde (Indicador Rojo + 1) en adelante (sin límite superior).",
    )
