# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    purchase_approval_user_id = fields.Many2one(
        'res.users',
        string="Usuario que Aprueba Compras",
        help="Persona que recibe por correo las órdenes de compra enviadas "
             "a aprobación y cuyo enlace de un clic las confirma.",
    )
