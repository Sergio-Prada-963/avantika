# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    uvt_value = fields.Float(
        string='Valor UVT', digits='Account',
        help="Valor en COP de la Unidad de Valor Tributario (UVT) vigente. "
             "Se usa para calcular la base mínima de las retenciones que "
             "tienen activo 'Aplica Base UVT'.",
    )
