from odoo import api, fields, models


class ProductSupplierinfo(models.Model):
    _inherit = "product.supplierinfo"

    factor_importacion = fields.Float(string="Factor de Importación")
    min_qty = fields.Float(default=1.0)

    @api.onchange("partner_id")
    def _onchange_partner_id_factor_importacion(self):
        for line in self:
            line.factor_importacion = line.partner_id.factor_importacion
