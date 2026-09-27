# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    indicador_verde = fields.Integer(
        related='company_id.indicador_verde', readonly=False,
        string="Indicador Verde (días)",
    )
    indicador_amarillo = fields.Integer(
        related='company_id.indicador_amarillo', readonly=False,
        string="Indicador Amarillo (días)",
    )
    indicador_rojo = fields.Integer(
        related='company_id.indicador_rojo', readonly=False,
        string="Indicador Rojo (días)",
    )
    indicador_negro = fields.Integer(
        related='company_id.indicador_negro', readonly=False,
        string="Indicador Negro (días)",
    )
