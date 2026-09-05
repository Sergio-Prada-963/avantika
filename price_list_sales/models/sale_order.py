# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    pricelist_sector_warning = fields.Char(
        string="Advertencia de Sector",
        compute="_compute_pricelist_sector_warning",
    )
    seller_mismatch_warning = fields.Text(
        string="Advertencia de Proveedor",
        compute="_compute_seller_mismatch_warning",
    )
    allowed_pricelist_ids = fields.Many2many(
        "product.pricelist",
        compute="_compute_allowed_pricelist_ids",
        string="Listas de Precios Permitidas",
    )

    @api.depends("partner_id.state_id")
    @api.depends_context("uid")
    def _compute_allowed_pricelist_ids(self):
        for order in self:
            order.allowed_pricelist_ids = self.env[
                "product.pricelist"
            ]._get_department_allowed_pricelists(order.partner_id)

    @api.depends("partner_id.state_id")
    @api.depends_context("uid")
    def _compute_pricelist_id(self):
        super()._compute_pricelist_id()
        for order in self:
            if order.state != "draft" or not order.partner_id:
                continue
            allowed = order.allowed_pricelist_ids
            order.pricelist_id = allowed if len(allowed) == 1 else False

    @api.depends("pricelist_id", "partner_id.x_studio_sector_1", "partner_id.x_studio_subsector_1")
    def _compute_pricelist_sector_warning(self):
        for order in self:
            sector = order.partner_id.x_studio_sector_1
            sub_sector = order.partner_id.x_studio_subsector_1
            has_match = order.pricelist_id.item_ids.filtered(
                lambda i: sector in i.sector_ids and sub_sector in i.sub_sector_ids
            )
            order.pricelist_sector_warning = (
                _("El sector del cliente no está en esta lista de precios.")
                if order.pricelist_id and not has_match
                else False
            )

    @api.depends("order_line.seller_mismatch")
    def _compute_seller_mismatch_warning(self):
        for order in self:
            mismatched = order.order_line.filtered("seller_mismatch")
            order.seller_mismatch_warning = (
                _("Los productos resaltados en naranja no tiene establecidas listas de precios del proveedor")
                if mismatched
                else False
            )

    def _recompute_prices(self):
        # El botón nativo "Actualizar Precios" solo invalida `pricelist_item_id`
        # (no almacenado) antes de recalcular `price_unit`. Nuestros campos de
        # referencia (ExWork, TRM, etc.) son `store=True`: invalidar su caché
        # no sirve para forzar su recálculo, ya que al releerlos el ORM trae
        # el valor ya persistido en BD en vez de recalcularlo. Además
        # dependen de datos que no se pueden declarar como dependencia (la
        # tabla de tasas de cambio); hay que recalcularlos explícitamente
        # para que tomen el precio del proveedor y la TRM vigentes al
        # momento de presionar el botón.
        lines_to_recompute = self._get_update_prices_lines()
        lines_to_recompute._compute_pricelist_line_id()
        lines_to_recompute._compute_pricing_reference_fields()
        super()._recompute_prices()
