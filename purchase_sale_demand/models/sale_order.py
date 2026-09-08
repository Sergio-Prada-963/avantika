# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    already_purchased = fields.Boolean(
        string="Ya fue Comprado",
        help="Marca esta orden como ya comprada para que sus líneas dejen "
             "de aparecer en el listado de Compra por Demanda, aunque "
             "todavía tengan cantidad pendiente por comprar.",
    )
