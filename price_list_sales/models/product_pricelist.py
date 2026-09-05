# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    state_ids = fields.Many2many(
        "res.country.state",
        string="Departamento",
        help="Departamentos a los que aplica esta lista de precios. Si se "
             "deja vacío, aplica a cualquier departamento.",
    )

    @api.model
    def _get_department_allowed_pricelists(self, partner):
        """Listas de precios cuyo departamento coincide con el del contacto
        (o que no tienen departamento configurado, es decir aplican a
        cualquiera), filtradas además a las que el usuario actual tiene
        permiso de usar."""
        state = partner.state_id
        domain = [("state_ids", "=", False)]
        if state:
            domain = ["|", ("state_ids", "=", False), ("state_ids", "in", state.id)]
        pricelists = self.search(domain)

        user = self.env.user
        if not user.pricelist_see_all:
            pricelists &= user.allowed_pricelist_ids
        return pricelists
