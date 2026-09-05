# -*- coding: utf-8 -*-
from odoo import api, fields, models

CUSTOMER_INVOICE_TYPES = ("out_invoice", "out_refund")


class AccountMove(models.Model):
    _inherit = "account.move"

    pricelist_id = fields.Many2one(
        "product.pricelist",
        string="Lista de Precios",
        copy=False,
    )
    allowed_pricelist_ids = fields.Many2many(
        "product.pricelist",
        compute="_compute_allowed_pricelist_ids",
        string="Listas de Precios Permitidas",
    )

    @api.depends("partner_id.state_id")
    @api.depends_context("uid")
    def _compute_allowed_pricelist_ids(self):
        for move in self:
            move.allowed_pricelist_ids = self.env[
                "product.pricelist"
            ]._get_department_allowed_pricelists(move.partner_id)

    @api.onchange("partner_id")
    def _onchange_partner_id_department_pricelist(self):
        for move in self:
            if move.move_type not in CUSTOMER_INVOICE_TYPES or move.state != "draft":
                continue
            allowed = move.allowed_pricelist_ids
            move.pricelist_id = allowed if len(allowed) == 1 else False
