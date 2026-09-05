# -*- coding: utf-8 -*-
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    pricelist_see_all = fields.Boolean(
        string="Ver Todas las Listas de Precios", default=True,
    )
    allowed_pricelist_ids = fields.Many2many(
        "product.pricelist",
        string="Listas de Precios Permitidas",
        help="Listas de precios que este usuario puede usar cuando no tiene "
             "marcado \"Ver Todas las Listas de Precios\".",
    )
