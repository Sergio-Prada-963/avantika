# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    uvt_value = fields.Float(
        string='Valor UVT', digits='Account',
        help="Valor en COP de la Unidad de Valor Tributario (UVT) vigente. "
             "Se usa para calcular la base mínima de las retenciones que "
             "tienen activo 'Aplica Base UVT'. En 0, el módulo no toca los "
             "impuestos.",
    )
    wbt_no_product_mode = fields.Selection([
        ('goods', 'Bien'),
        ('service', 'Servicio'),
        ('exclude', 'Excluir'),
    ], string='Líneas sin producto', default='exclude', required=True,
        help="Cómo se tratan, para las retenciones, las líneas que no tienen "
             "producto: como bien, como servicio, o excluidas de toda retención.")
