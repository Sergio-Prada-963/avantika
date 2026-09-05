# -*- coding: utf-8 -*-
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    approve_sale_margins = fields.Boolean(string="Aprobar Márgenes de Venta")
    can_edit_price_unit = fields.Boolean(string="Editar Precio Unitario en Ventas")
