from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    sector_ids = fields.Many2many("x_sectores", string="Sectores")
    sub_sector_ids = fields.Many2many("x_subsector", string="Sub Sectores")
    proveedor_id = fields.Many2one("res.partner", string="Proveedor")
    rentabilidad = fields.Integer(string="Rentabilidad")
    base = fields.Selection(
        selection_add=[("proveedor", "Basado en el Proveedor")],
        ondelete={"proveedor": "set default"},
    )

    @api.constrains("rentabilidad")
    def _check_rentabilidad(self):
        for item in self:
            if item.rentabilidad >= 100:
                raise ValidationError(_("La rentabilidad debe ser menor a 100."))

    def _compute_price(self, product, quantity, uom, date, currency=None, **kwargs):
        if self.compute_price == "formula" and self.base == "proveedor":
            if kwargs.get("seller_mismatch"):
                return 0.0

            if "exwork" in kwargs:
                # Fuente única de verdad: los datos ya calculados en la línea de venta
                # (el ajuste de TRM x 1.05, si aplica, ya viene incluido en exwork).
                exwork = kwargs.get("exwork") or 0.0
                factor_importacion = kwargs.get("factor_importacion") or 1
                rentabilidad = kwargs.get("factor_rentabilidad", self.rentabilidad)
            else:
                # Fallback para llamadas fuera del flujo de venta (sin línea de venta).
                # Compara únicamente la moneda del pedido/lista (currency) contra
                # la del proveedor -- la moneda de la compañía no interviene en
                # la comparación, igual que en
                # sale.order.line._get_seller_conversion_rate.
                seller = product.seller_ids.filtered(
                    lambda s: s.partner_id == self.proveedor_id
                )[:1] or product.seller_ids[:1]
                factor_importacion = seller.factor_importacion or 1
                raw_price = seller.price if seller else 0.0
                order_currency = currency or self.env.company.currency_id
                seller_currency = seller.currency_id
                if seller and seller_currency and seller_currency != order_currency:
                    trm = self.env["res.currency"]._get_conversion_rate(
                        seller_currency, order_currency, self.env.company, date
                    )
                    exwork = raw_price * trm * 1.05
                else:
                    exwork = raw_price
                rentabilidad = self.rentabilidad

            if not rentabilidad or rentabilidad >= 100:
                return 0.0

            return exwork * factor_importacion / ((100 - rentabilidad) / 100)

        return super()._compute_price(product, quantity, uom, date, currency=currency, **kwargs)
