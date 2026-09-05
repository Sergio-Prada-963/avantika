# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    uvt_value = fields.Float(
        related='company_id.uvt_value', readonly=False, digits='Account',
        string='Valor UVT',
    )
