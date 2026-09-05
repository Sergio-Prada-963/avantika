from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    pricelist_line_id = fields.Many2one(
        "product.pricelist.item",
        string="Línea de Lista de Precios",
        compute="_compute_pricelist_line_id",
        store=True,
    )
    exwork = fields.Float(
        string="ExWork", compute="_compute_pricing_reference_fields", store=True
    )
    factor_importacion = fields.Float(
        string="Factor de Importación",
        compute="_compute_pricing_reference_fields",
        store=True,
    )
    trm = fields.Float(
        string="TRM", compute="_compute_pricing_reference_fields", store=True
    )
    factor_rentabilidad = fields.Float(
        string="Factor Rentabilidad",
        compute="_compute_pricing_reference_fields",
        store=True,
    )
    seller_mismatch = fields.Boolean(
        string="Proveedor No Coincide",
        compute="_compute_pricelist_line_id",
        store=True,
    )

    def _get_pricelist_kwargs(self):
        kwargs = super()._get_pricelist_kwargs()
        kwargs["exwork"] = self.exwork
        kwargs["factor_importacion"] = self.factor_importacion
        kwargs["factor_rentabilidad"] = self.factor_rentabilidad
        kwargs["seller_mismatch"] = self.seller_mismatch
        return kwargs

    @api.depends(
        "product_id",
        "product_id.seller_ids.partner_id",
        "order_id.pricelist_id",
        "order_id.partner_id.x_studio_sector_1",
        "order_id.partner_id.x_studio_subsector_1",
    )
    def _compute_pricelist_line_id(self):
        for line in self:
            if line.product_id and line._is_kit():
                # El precio de un kit se arma sumando el de cada componente
                # de su lista de materiales, no el de un único proveedor.
                line.pricelist_line_id = False
                line.seller_mismatch = False
                continue

            order = line.order_id
            sector = order.partner_id.x_studio_sector_1
            sub_sector = order.partner_id.x_studio_subsector_1
            candidates = order.pricelist_id.item_ids.filtered(
                lambda i: sector in i.sector_ids and sub_sector in i.sub_sector_ids
            )

            matched = self.env["product.pricelist.item"]
            if line.product_id:
                # Se respeta la prioridad de proveedores del producto (orden
                # de secuencia en su lista de precios de compra): se toma el
                # primero que además tenga ítem en la lista de precios de
                # venta del pedido.
                for seller in line.product_id.seller_ids:
                    matched = candidates.filtered(
                        lambda i: i.proveedor_id == seller.partner_id
                    )[:1]
                    if matched:
                        break

            line.pricelist_line_id = matched
            line.seller_mismatch = bool(candidates and line.product_id and not matched)

    def _get_seller_conversion_rate(self, seller):
        """Tasa para convertir el precio del proveedor (en su propia moneda)
        a la moneda del pedido de venta, según la tabla de tasas de cambio
        para la fecha del pedido. No se compara ni se pasa por la moneda de
        la compañía en ningún momento: solo importan la moneda del
        proveedor y la del pedido. 1.0 si ambas monedas coinciden."""
        self.ensure_one()
        order_currency = self.order_id.currency_id or self.order_id.company_id.currency_id
        seller_currency = seller.currency_id
        if not seller or not seller_currency or seller_currency == order_currency:
            return 1.0
        date = (self.order_id.date_order or fields.Datetime.now()).date()
        return self.env["res.currency"]._get_conversion_rate(
            seller_currency, order_currency, self.order_id.company_id, date
        )

    def _apply_seller_conversion(self, raw_price, seller):
        """Ajusta el precio del proveedor (en su propia moneda) a la moneda
        del pedido de venta, multiplicando por TRM x 1.05 cuando las
        monedas difieren. Devuelve (precio_ajustado, trm)."""
        self.ensure_one()
        trm = self._get_seller_conversion_rate(seller)
        if trm == 1.0:
            return raw_price, trm
        return raw_price * trm * 1.05, trm

    @api.depends(
        "pricelist_line_id", "product_id",
        "product_id.seller_ids.price",
        "product_id.seller_ids.factor_importacion",
        "product_id.seller_ids.currency_id",
        "order_id.company_id", "order_id.currency_id", "order_id.date_order",
    )
    def _compute_pricing_reference_fields(self):
        for line in self:
            if line.product_id and line._is_kit():
                # Estos campos son informativos de un único proveedor y no
                # aplican a un kit, cuyo precio es la suma de componentes.
                line.exwork = 0.0
                line.factor_importacion = 0.0
                line.trm = 0.0
                line.factor_rentabilidad = 0.0
                continue

            pricelist_line = line.pricelist_line_id
            proveedor = pricelist_line.proveedor_id
            seller = self.env["product.supplierinfo"]
            if proveedor and line.product_id:
                seller = line.product_id.seller_ids.filtered(
                    lambda s: s.partner_id == proveedor
                )[:1]

            raw_price = seller.price if seller else 0.0
            line.exwork, line.trm = line._apply_seller_conversion(raw_price, seller)
            line.factor_importacion = seller.factor_importacion or 0.0
            line.factor_rentabilidad = pricelist_line.rentabilidad or 0.0

    def _is_kit(self):
        """Un kit es un producto con una lista de materiales asociada
        (creado, por ejemplo, con el botón "Agregar Kit" de sale_order_custom)."""
        self.ensure_one()
        return bool(self._get_kit_bom())

    def _get_kit_bom(self):
        self.ensure_one()
        if not self.product_id:
            return self.env["mrp.bom"]
        return self.env["mrp.bom"]._bom_find(self.product_id)[self.product_id]

    def _compute_kit_price(self):
        """Precio de un kit: la suma del precio de cada componente de su
        lista de materiales, calculado como si cada componente fuera el
        producto de esta línea de venta (misma fórmula de proveedor)."""
        self.ensure_one()
        bom = self._get_kit_bom()
        if not bom or not bom.product_qty:
            return 0.0

        total = 0.0
        for bom_line in bom.bom_line_ids:
            qty_per_kit_unit = bom_line.product_qty / bom.product_qty
            total += self._compute_component_price(bom_line.product_id, qty_per_kit_unit)
        return total

    def _compute_component_price(self, component_product, component_qty):
        """Calcula el precio de un componente del kit aplicando la misma
        fórmula de lista de precios (basada en proveedor) que se usaría si
        ese componente fuera directamente el producto de esta línea."""
        self.ensure_one()
        order = self.order_id
        sector = order.partner_id.x_studio_sector_1
        sub_sector = order.partner_id.x_studio_subsector_1
        candidates = order.pricelist_id.item_ids.filtered(
            lambda i: sector in i.sector_ids and sub_sector in i.sub_sector_ids
        )
        pricelist_line = self.env["product.pricelist.item"]
        for seller in component_product.seller_ids:
            pricelist_line = candidates.filtered(
                lambda i: i.proveedor_id == seller.partner_id
            )[:1]
            if pricelist_line:
                break
        if not pricelist_line or pricelist_line.base != "proveedor":
            return 0.0

        rentabilidad = pricelist_line.rentabilidad or 0.0
        if not rentabilidad or rentabilidad >= 100:
            return 0.0

        seller = component_product.seller_ids.filtered(
            lambda s: s.partner_id == pricelist_line.proveedor_id
        )[:1]
        raw_price = seller.price if seller else 0.0
        exwork, __ = self._apply_seller_conversion(raw_price, seller)
        factor_importacion = seller.factor_importacion or 0.0

        price = exwork * (factor_importacion or 1) / ((100 - rentabilidad) / 100)
        return price * component_qty

    @api.depends(
        "product_id",
        "product_uom_id",
        "product_uom_qty",
        "exwork",
        "factor_importacion",
        "trm",
        "factor_rentabilidad",
        "seller_mismatch",
    )
    def _compute_price_unit(self):
        super()._compute_price_unit()
        for line in self:
            if not line.order_id or line.is_downpayment or line._is_global_discount():
                continue

            if line.product_id and line._is_kit():
                kit_price = line._compute_kit_price()
                if not kit_price:
                    continue
                line = line.with_context(sale_write_from_compute=True)
                line.price_unit = kit_price
                line.technical_price_unit = kit_price
                continue

            pricelist_line = line.pricelist_line_id
            if (
                not pricelist_line
                or pricelist_line.base != "proveedor"
                or not pricelist_line.proveedor_id
                or line.seller_mismatch
                or line.factor_rentabilidad >= 100
            ):
                continue

            price = line.exwork * (line.factor_importacion or 1) / (
                (100 - line.factor_rentabilidad) / 100
            )

            line = line.with_context(sale_write_from_compute=True)
            line.price_unit = price
            line.technical_price_unit = price
