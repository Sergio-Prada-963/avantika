# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    city_declaration_id = fields.Many2one(
        'res.city',
        string='Ciudad de Declaración ReteICA',
        help="Municipio en el que este contacto declara ICA. Se usa por "
             "defecto en sus órdenes de venta y facturas para determinar la "
             "retención de ReteICA municipal aplicable, según la 'Tarifa "
             "ReteICA por Municipio' configurada para esa ciudad.",
    )
