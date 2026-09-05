# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    aiu_administracion_product_id = fields.Many2one(
        "product.product", string="Producto de Administración (AIU)")
    aiu_imprevistos_product_id = fields.Many2one(
        "product.product", string="Producto de Imprevistos (AIU)")
    aiu_utilidades_product_id = fields.Many2one(
        "product.product", string="Producto de Utilidades (AIU)")
