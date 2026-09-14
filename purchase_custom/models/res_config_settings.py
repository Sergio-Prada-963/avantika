# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    aiu_purchase_administracion_product_id = fields.Many2one(
        related="company_id.aiu_purchase_administracion_product_id",
        string="Producto de Administración (AIU Compras)", readonly=False)
    aiu_purchase_imprevistos_product_id = fields.Many2one(
        related="company_id.aiu_purchase_imprevistos_product_id",
        string="Producto de Imprevistos (AIU Compras)", readonly=False)
    aiu_purchase_utilidades_product_id = fields.Many2one(
        related="company_id.aiu_purchase_utilidades_product_id",
        string="Producto de Utilidades (AIU Compras)", readonly=False)

    purchase_approval_user_id = fields.Many2one(
        "res.users",
        related="company_id.purchase_approval_user_id",
        string="Usuario que Aprueba Compras",
        readonly=False,
    )
