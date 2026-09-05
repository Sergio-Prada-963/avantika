# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    aiu_administracion_product_id = fields.Many2one(
        related="company_id.aiu_administracion_product_id",
        string="Producto de Administración (AIU)", readonly=False)
    aiu_imprevistos_product_id = fields.Many2one(
        related="company_id.aiu_imprevistos_product_id",
        string="Producto de Imprevistos (AIU)", readonly=False)
    aiu_utilidades_product_id = fields.Many2one(
        related="company_id.aiu_utilidades_product_id",
        string="Producto de Utilidades (AIU)", readonly=False)
