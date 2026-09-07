# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    purchase_approval_user_id = fields.Many2one(
        'res.users',
        related='company_id.purchase_approval_user_id',
        string="Usuario que Aprueba Compras",
        readonly=False,
    )
