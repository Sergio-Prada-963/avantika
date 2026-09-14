# -*- coding: utf-8 -*-
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    show_confirm_button_purchase_no_approval = fields.Boolean(
        string="Confirmar Compras sin Aprobación",
        help="Muestra el botón \"Confirmar\" en las órdenes de compra en "
             "estado Borrador y Por Aprobar, permitiendo a este usuario "
             "confirmarlas directamente sin pasar por el flujo de "
             "aprobación por correo.",
    )
