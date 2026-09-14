# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    aiu_purchase_administracion_product_id = fields.Many2one(
        "product.product", string="Producto de Administración (AIU Compras)")
    aiu_purchase_imprevistos_product_id = fields.Many2one(
        "product.product", string="Producto de Imprevistos (AIU Compras)")
    aiu_purchase_utilidades_product_id = fields.Many2one(
        "product.product", string="Producto de Utilidades (AIU Compras)")

    purchase_approval_user_id = fields.Many2one(
        "res.users",
        string="Usuario que Aprueba Compras",
        help="Persona que recibe por correo las órdenes de compra enviadas "
             "a aprobación y cuyo enlace de un clic las confirma.",
    )
