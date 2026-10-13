# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    stock_move_indicador_verde = fields.Integer(
        related='company_id.stock_move_indicador_verde', readonly=False,
        string="Indicador Verde (días de atraso)",
    )
    stock_move_indicador_amarillo = fields.Integer(
        related='company_id.stock_move_indicador_amarillo', readonly=False,
        string="Indicador Amarillo (días de atraso)",
    )
    stock_move_indicador_rojo = fields.Integer(
        related='company_id.stock_move_indicador_rojo', readonly=False,
        string="Indicador Rojo (días de atraso)",
    )
    stock_move_indicador_negro = fields.Integer(
        related='company_id.stock_move_indicador_negro', readonly=False,
        string="Indicador Negro (días de atraso)",
    )
