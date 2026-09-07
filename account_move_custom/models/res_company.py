# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    economic_activity_code = fields.Char(string="Código Actividad Económica")
    economic_activity_name = fields.Char(string="Nombre Actividad Económica")

    dian_resolution_number = fields.Char(string="Número de Resolución DIAN")
    dian_resolution_date_from = fields.Date(string="Vigencia Desde")
    dian_resolution_date_to = fields.Date(string="Vigencia Hasta")
    dian_resolution_range_from = fields.Char(string="Numeración Desde")
    dian_resolution_range_to = fields.Char(string="Numeración Hasta")
    dian_tech_provider_name = fields.Char(string="Proveedor Tecnológico")
    dian_tech_provider_vat = fields.Char(string="NIT del Proveedor Tecnológico")
    dian_software_name = fields.Char(string="Nombre del Software")
