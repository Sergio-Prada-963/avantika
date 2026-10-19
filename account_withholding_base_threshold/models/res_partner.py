# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    wbt_reteica_agent = fields.Boolean(
        string='Me retiene ICA',
        help="Cliente que le practica ReteICA a la compañía. El ReteICA de "
             "ventas solo se aplica si este indicador está marcado y la "
             "posición fiscal del documento está en el impuesto.",
    )
    wbt_reteica_tax_ids = fields.Many2many(
        'account.tax', 'res_partner_wbt_reteica_tax_rel', 'partner_id', 'tax_id',
        string='Tarifas ReteICA',
        domain="[('is_reteica', '=', True), ('type_tax_use', '=', 'purchase')]",
        help="Tarifas de ReteICA de compras que se le practican a este "
             "proveedor según su actividad (una por municipio). Se aplica la "
             "que coincida con la ciudad de la operación.",
    )

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ['wbt_reteica_agent', 'wbt_reteica_tax_ids']
