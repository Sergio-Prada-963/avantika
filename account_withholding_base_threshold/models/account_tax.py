# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountTax(models.Model):
    _inherit = 'account.tax'

    uvt_base = fields.Boolean(
        string='Aplica Base UVT',
        help="Si está activo, esta retención solo se aplica automáticamente "
             "cuando la base gravable (en UVT) alcanza la 'Cantidad UVT' "
             "configurada abajo. Se agrega o se quita de las líneas de forma "
             "automática mientras la factura está en borrador.",
    )
    uvt_base_type = fields.Selection([
        ('total', 'Total de la Factura'),
        ('lines', 'Líneas de la Factura'),
    ], string='Base para Calcular', default='lines',
        help="Determina qué monto se compara contra la base mínima en UVT: "
             "el total de la factura completa, o solo la suma de las líneas "
             "a las que esta retención aplicaría.")
    uvt_quantity = fields.Float(
        string='Cantidad UVT', digits='Account',
        help="Número de UVT que debe alcanzar la base gravable para que "
             "esta retención se aplique. Se compara contra 'Cantidad UVT' × "
             "'Valor UVT' (configurado en Contabilidad).",
    )
    is_reteica = fields.Boolean(
        string='Es ReteICA Municipal',
        help="Marca esta retención como la ReteICA de un municipio "
             "específico ('Ciudad / Municipio' abajo). Solo se aplicará "
             "automáticamente en órdenes/facturas cuyo cliente tenga esa "
             "misma ciudad como 'Ciudad de Declaración ReteICA'.",
    )
    city_id = fields.Many2one(
        'res.city', string='Ciudad / Municipio',
        help="Municipio de esta retención de ReteICA. Solo se aplica a "
             "órdenes o facturas cuyo cliente declare ICA en esta misma "
             "ciudad. Recuerda además activar 'Aplica Base UVT' para "
             "definir la base mínima de este municipio.",
    )

    @api.constrains('uvt_base', 'uvt_quantity')
    def _check_uvt_quantity(self):
        for tax in self:
            if tax.uvt_base and tax.uvt_quantity <= 0:
                raise ValidationError(_(
                    'La "Cantidad UVT" debe ser mayor que cero en la retención "%s" '
                    'cuando "Aplica Base UVT" está activo.', tax.name))

    @api.constrains('is_reteica', 'city_id')
    def _check_reteica_city(self):
        for tax in self:
            if tax.is_reteica and not tax.city_id:
                raise ValidationError(_(
                    'Debe seleccionar la "Ciudad / Municipio" en la retención "%s" '
                    'cuando "Es ReteICA Municipal" está activo.', tax.name))
