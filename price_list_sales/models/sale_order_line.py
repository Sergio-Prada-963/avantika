from odoo import api, fields, models

# Rentabilidad aplicada cuando una línea no encuentra ninguna línea de lista
# de precios de venta (ningún proveedor del producto tiene ítem en la lista
# de precios del pedido): se toma igualmente el primer proveedor de la lista
# de precios de COMPRA del producto (por orden de secuencia) y se calcula el
# exwork normalmente, pero con esta rentabilidad objetivo en vez de la del
# ítem de lista de precios (que no existe en este caso).
FALLBACK_RENTABILIDAD = 55


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
    supplierinfo_id = fields.Many2one(
        "product.supplierinfo",
        string="Proveedor de Referencia (ExWork)",
        compute="_compute_pricelist_line_id",
        store=True,
    )

    def _has_manual_price(self):
        # Regla explícita del negocio: un precio distinto de 0 nunca se debe
        # recalcular automáticamente (sin importar si llegó ahí por una
        # edición manual o por un cálculo previo); solo se toca si el precio
        # sigue en 0, o si se fuerza desde el botón "Actualizar Precios".
        self.ensure_one()
        currency = (
            self.currency_id
            or self.company_id.currency_id
            or self.env.company.currency_id
        )
        return not currency.is_zero(self.price_unit)

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
        # También resuelve y guarda `supplierinfo_id`: el proveedor concreto
        # (registro de `product.supplierinfo`) que se debe usar para calcular
        # el exwork, tanto si viene de un ítem de lista de precios de venta
        # como si es el proveedor de respaldo (55% de rentabilidad).
        for line in self:
            if line.product_id and line._is_kit():
                # El precio de un kit se arma sumando el de cada componente
                # de su lista de materiales, no el de un único proveedor.
                line.pricelist_line_id = False
                line.seller_mismatch = False
                line.supplierinfo_id = False
                continue

            order = line.order_id
            sector = order.partner_id.x_studio_sector_1
            sub_sector = order.partner_id.x_studio_subsector_1
            candidates = order.pricelist_id.item_ids.filtered(
                lambda i: sector in i.sector_ids and sub_sector in i.sub_sector_ids
            )

            matched = self.env["product.pricelist.item"]
            matched_seller = self.env["product.supplierinfo"]
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
                        matched_seller = seller
                        break

            line.pricelist_line_id = matched
            line.seller_mismatch = bool(candidates and line.product_id and not matched)

            if matched_seller:
                line.supplierinfo_id = matched_seller
            elif line.product_id and line.product_id.seller_ids:
                # Sin ítem de lista de precios de venta: se guarda igual el
                # primer proveedor de la lista de precios de compra del
                # producto, que es el que se usará para calcular el exwork
                # con la rentabilidad de respaldo.
                line.supplierinfo_id = line.product_id.seller_ids[:1]
            else:
                line.supplierinfo_id = False

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
        "pricelist_line_id", "supplierinfo_id", "product_id",
        "supplierinfo_id.price",
        "supplierinfo_id.factor_importacion",
        "supplierinfo_id.currency_id",
        "order_id.company_id", "order_id.currency_id", "order_id.date_order",
    )
    def _compute_pricing_reference_fields(self):
        for line in self:
            if line.product_id and line._is_kit():
                # factor_importacion/trm/factor_rentabilidad son informativos
                # de un único proveedor y no aplican a un kit. exwork sí: es
                # la suma del costo total (component_cost, "Costo Total EXW")
                # de cada componente de su lista de materiales -- esos campos
                # ya calculan el costo de cada componente con su propio
                # proveedor/factor de importación (ver mrp.bom._get_component_cost)
                # -- normalizada a 1 unidad del kit (bom.product_qty puede no ser 1).
                bom = line._get_kit_bom()
                if bom and bom.product_qty:
                    line.exwork = sum(bom.bom_line_ids.mapped('component_cost')) / bom.product_qty
                else:
                    line.exwork = 0.0
                line.factor_importacion = 0.0
                line.trm = 0.0
                line.factor_rentabilidad = 0.0
                continue

            # El proveedor a usar ya quedó guardado en `supplierinfo_id`
            # (resuelto en `_compute_pricelist_line_id`), sea el del ítem de
            # lista de precios de venta o el de respaldo.
            seller = line.supplierinfo_id
            pricelist_line = line.pricelist_line_id
            if seller and pricelist_line.proveedor_id == seller.partner_id:
                rentabilidad = pricelist_line.rentabilidad or 0.0
            elif seller:
                rentabilidad = FALLBACK_RENTABILIDAD
            else:
                rentabilidad = 0.0

            raw_price = seller.price if seller else 0.0
            converted_price, line.trm = line._apply_seller_conversion(raw_price, seller)
            factor_importacion = seller.factor_importacion or 0.0
            line.factor_importacion = factor_importacion
            # El factor de importación queda incluido en exwork (no se
            # multiplica aparte en ningún lado más: ver _compute_price_unit,
            # _compute_component_price y product_pricelist_item._compute_price).
            line.exwork = converted_price * (factor_importacion or 1)
            line.factor_rentabilidad = rentabilidad

    def _is_kit(self):
        """Un kit es un producto con una lista de materiales asociada
        (creado, por ejemplo, con el botón "Agregar Kit" de sale_order_custom)."""
        self.ensure_one()
        return bool(self._get_kit_bom())

    def _get_kit_bom(self):
        self.ensure_one()
        if not self.product_id:
            return self.env["mrp.bom"]
        # `bom_type='phantom'`: sin esto, `_bom_find` trae la primera BOM de
        # CUALQUIER tipo para el producto. Un componente del kit puede tener
        # su propia BOM normal de fabricación (ser una sub-pieza fabricada)
        # sin por eso ser "un kit" en sí mismo; sin este filtro, esa línea
        # entraba por error en la rama de kit y se quedaba sin proveedor
        # (`supplierinfo_id`), ya que esa rama no resuelve proveedor.
        return self.env["mrp.bom"]._bom_find(
            self.product_id, bom_type="phantom"
        )[self.product_id]

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
        converted_price, __ = self._apply_seller_conversion(raw_price, seller)
        factor_importacion = seller.factor_importacion or 0.0
        exwork = converted_price * (factor_importacion or 1)

        price = exwork / ((100 - rentabilidad) / 100)
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
        force_recompute = self.env.context.get('force_price_recomputation')

        # Igual que el core (`has_manual_price` en sale.order.line): si el
        # precio fue editado a mano, no se debe pisar en recálculos
        # posteriores (p. ej. al confirmar la orden, que siempre reescribe
        # `date_order` y eso dispara este compute vía `exwork`/`trm`/etc.),
        # salvo que el recálculo se haya pedido explícitamente (botón
        # "Actualizar Precios", que pasa `force_price_recomputation`).
        # OJO: el `super()` (core) NO debe llamarse para estas líneas
        # protegidas -- su propia protección compara `technical_price_unit`
        # contra `price_unit`, que en nuestro flujo suelen quedar iguales a
        # propósito, así que el core las trataría como "no manuales" y
        # las resetearía con su propia lógica de lista de precios estándar.
        def is_protected(line):
            return bool(
                line.order_id
                and not line.is_downpayment
                and not line._is_global_discount()
                and not force_recompute
                and line._has_manual_price()
            )

        to_process = self.filtered(lambda line: not is_protected(line))
        super(SaleOrderLine, to_process)._compute_price_unit()

        for line in to_process:
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

            if not line.product_id:
                continue

            pricelist_line = line.pricelist_line_id
            has_pricelist_seller = bool(
                pricelist_line
                and pricelist_line.base == "proveedor"
                and pricelist_line.proveedor_id
                and not line.seller_mismatch
            )
            # Si no hay línea de lista de precios (ningún proveedor del
            # producto tiene ítem en la lista de precios del pedido), se usa
            # igual el primer proveedor de la lista de precios de compra del
            # producto (ya resuelto en `_compute_pricing_reference_fields`,
            # que llenó exwork/factor_importacion/factor_rentabilidad con la
            # rentabilidad de respaldo) siempre que el producto tenga algún
            # proveedor configurado.
            has_fallback_seller = bool(not pricelist_line and line.product_id.seller_ids)

            if not has_pricelist_seller and not has_fallback_seller:
                continue
            if line.factor_rentabilidad >= 100:
                continue

            # factor_importacion ya viene incluido en exwork (ver
            # _compute_pricing_reference_fields), no se multiplica aquí de nuevo.
            price = line.exwork / ((100 - line.factor_rentabilidad) / 100)

            line = line.with_context(sale_write_from_compute=True)
            line.price_unit = price
            line.technical_price_unit = price
