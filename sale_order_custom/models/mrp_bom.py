# -*- coding: utf-8 -*-
from odoo import _, api, models
from odoo.exceptions import UserError


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    @api.model_create_multi
    def create(self, vals_list):
        is_kit = self.env.context.get('kit')
        if is_kit:
            for vals in vals_list:
                if not vals.get('product_tmpl_id'):
                    vals['product_tmpl_id'] = self._create_kit_product_template(vals).id

        boms = super().create(vals_list)

        if is_kit:
            boms._compute_kit_product_cost()
            boms._add_kit_line_to_sale_order()

        return boms

    def _create_kit_product_template(self, vals):
        component_name = self._get_first_component_name(vals)
        return self.env['product.template'].create({
            'name': _("Kit %s") % component_name,
            'type': 'consu',
            'is_storable': False,
            'purchase_ok': False,
        })

    def _get_first_component_name(self, vals):
        for command in vals.get('bom_line_ids') or []:
            line_vals = command[2] if len(command) > 2 else {}
            product_id = line_vals.get('product_id')
            if product_id:
                return self.env['product.product'].browse(product_id).name
        raise UserError(_("Debe agregar al menos un componente para crear el kit."))

    def _compute_kit_product_cost(self):
        for bom in self:
            bom.product_tmpl_id.product_variant_id.button_bom_cost()

    def _add_kit_line_to_sale_order(self):
        order_id = self.env.context.get('kit_sale_order_id')
        if not order_id:
            return
        order = self.env['sale.order'].browse(order_id)
        if not order.exists():
            raise UserError(_("No se encontró la cotización para agregar el kit."))
        for bom in self:
            product = bom.product_tmpl_id.product_variant_id
            self.env['sale.order.line'].create({
                'order_id': order.id,
                'product_id': product.id,
                'product_uom_id': product.uom_id.id,
                'product_uom_qty': 1.0,
                'price_unit': product.lst_price,
            })
