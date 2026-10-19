# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountTax(models.Model):
    _inherit = 'account.tax'

    uvt_base = fields.Boolean(
        string='Aplica Base UVT',
        help="Si está activo, esta retención solo se aplica automáticamente "
             "cuando la base gravable (convertida a la moneda de la compañía) "
             "alcanza 'Cantidad UVT' × 'Valor UVT'. Con 0 UVT aplica siempre, "
             "respetando posición fiscal y alcance.",
    )
    uvt_base_type = fields.Selection([
        ('total', 'Total de la Factura'),
        ('lines', 'Líneas de la Factura'),
    ], string='Base para Calcular', default='lines',
        help="Total de la Factura: suma solo las líneas a las que aplica esta "
             "retención (alcance, categorías, IVA y, en ReteICA, el mismo "
             "municipio). Líneas de la Factura: evalúa cada línea por separado.")
    uvt_quantity = fields.Float(
        string='Cantidad UVT', digits='Account',
        help="Número de UVT que debe alcanzar la base. 0 = aplica siempre.",
    )
    is_reteica = fields.Boolean(
        string='Es ReteICA Municipal',
        help="Marca esta retención como el ReteICA de un municipio. Solo se "
             "aplica en las líneas cuya ciudad de operación coincida con "
             "'Ciudad / Municipio'.",
    )
    city_id = fields.Many2one(
        'res.city', string='Ciudad / Municipio',
        help="Municipio de este ReteICA.",
    )

    # A2: alcance de la retención por línea
    wbt_product_scope = fields.Selection([
        ('all', 'Todos'),
        ('goods', 'Bienes'),
        ('service', 'Servicios'),
    ], string='Alcance (tipo de producto)', default='all', required=True,
        help="Bienes = productos tipo Bienes (consumible/almacenable); "
             "Servicios = productos tipo Servicio. Las líneas sin producto "
             "se tratan según el ajuste de la compañía.")
    wbt_categ_ids = fields.Many2many(
        'product.category', 'account_tax_wbt_categ_rel', 'tax_id', 'categ_id',
        string='Solo categorías',
        help="Si tiene valor, la retención solo cae en líneas cuyo producto "
             "pertenezca a estas categorías o a sus hijas.")
    wbt_exclude_categ_ids = fields.Many2many(
        'product.category', 'account_tax_wbt_excl_categ_rel', 'tax_id', 'categ_id',
        string='Excluir categorías',
        help="La retención no cae en líneas de estas categorías (ni sus hijas).")
    wbt_required_tax_ids = fields.Many2many(
        'account.tax', 'account_tax_wbt_required_rel', 'tax_id', 'required_tax_id',
        string='Requiere IVA',
        help="Si tiene valor, la retención solo cae en líneas que tengan "
             "alguno de estos impuestos (ej. ReteIVA 15% solo con IVA 19%).")

    @api.constrains('uvt_base', 'uvt_quantity')
    def _check_uvt_quantity(self):
        # A5: 0 UVT es válido (aplica siempre).
        for tax in self:
            if tax.uvt_base and tax.uvt_quantity < 0:
                raise ValidationError(_(
                    'La "Cantidad UVT" no puede ser negativa en la retención "%s".',
                    tax.name))

    @api.constrains('is_reteica', 'city_id')
    def _check_reteica_city(self):
        for tax in self:
            if tax.is_reteica and not tax.city_id:
                raise ValidationError(_(
                    'Debe seleccionar la "Ciudad / Municipio" en la retención "%s" '
                    'cuando "Es ReteICA Municipal" está activo.', tax.name))

    # ------------------------------------------------------------------
    # Reglas
    # ------------------------------------------------------------------
    @api.model
    def _wbt_managed_domain(self, company, type_tax_use):
        """Impuestos que gestiona el módulo.

        Se excluyen los impuestos con "Reemplaza" (original_tax_ids): esos
        son cambios de IVA que hace la posición fiscal nativa de Odoo.
        """
        return [
            *self._check_company_domain(company),
            ('type_tax_use', '=', type_tax_use),
            ('original_tax_ids', '=', False),
            '|', '|',
            ('uvt_base', '=', True),
            ('is_reteica', '=', True),
            ('fiscal_position_ids', '!=', False),
        ]

    def _wbt_applies_to_fpos(self, fpos):
        """A1: la retención aplica solo en sus posiciones fiscales.

        Sin posiciones configuradas aplica siempre (ej. autorretención).
        """
        self.ensure_one()
        if not self.fiscal_position_ids:
            return True
        return bool(fpos) and fpos._origin in self.fiscal_position_ids._origin

    @staticmethod
    def _wbt_categ_matches(categ, categs):
        if not categ or not categs:
            return False
        ancestor_ids = {int(x) for x in (categ._origin.parent_path or '').split('/') if x}
        ancestor_ids.add(categ._origin.id)
        return bool(ancestor_ids & set(categs._origin.ids))

    def _wbt_line_in_scope(self, product, line_taxes, no_product_mode):
        """A2: ¿la retención cae en esta línea?

        :param product: product.product de la línea (puede estar vacío)
        :param line_taxes: impuestos de la línea que NO gestiona el módulo (IVA)
        :param no_product_mode: 'goods' | 'service' | 'exclude'
        """
        self.ensure_one()
        if product:
            kind = 'service' if product.type == 'service' else 'goods'
        else:
            if no_product_mode == 'exclude':
                return False
            kind = no_product_mode
        if self.wbt_product_scope != 'all' and self.wbt_product_scope != kind:
            return False
        categ = product.categ_id if product else self.env['product.category']
        if self.wbt_categ_ids and not self._wbt_categ_matches(categ, self.wbt_categ_ids):
            return False
        if self.wbt_exclude_categ_ids and self._wbt_categ_matches(categ, self.wbt_exclude_categ_ids):
            return False
        if self.wbt_required_tax_ids and not (line_taxes._origin & self.wbt_required_tax_ids._origin):
            return False
        return True
