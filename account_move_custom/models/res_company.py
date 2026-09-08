# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    economic_activity_code = fields.Char(string="Código Actividad Económica")
    economic_activity_name = fields.Char(string="Nombre Actividad Económica")
