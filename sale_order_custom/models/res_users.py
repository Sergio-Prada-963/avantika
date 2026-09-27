# -*- coding: utf-8 -*-
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    approve_sale_margins = fields.Boolean(string="Aprobar Márgenes de Venta")
    can_edit_price_unit = fields.Boolean(string="Editar Precio Unitario en Ventas")
    can_create_sales = fields.Boolean(
        string="Crear Ventas",
        help="Permite crear e importar órdenes de venta manualmente; por "
             "defecto solo se pueden generar desde el CRM.",
    )
    can_duplicate_sales = fields.Boolean(
        string="Duplicar Ventas",
        help="Permite duplicar una orden de venta existente (botón "
             "'Duplicar' propio en la orden), sin necesidad de tener "
             "también permiso para crear órdenes desde cero.",
    )
    show_confirm_button_sale = fields.Boolean(
        string="Mostrar Botón de Confirmar en Ventas", default=True,
    )
    skip_margin_validations = fields.Boolean(
        string="Omitir Validaciones de Margen en Ventas",
    )
