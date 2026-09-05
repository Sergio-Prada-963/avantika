from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    factor_importacion = fields.Float(string="Factor de Importación")
