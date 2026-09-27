# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    def _get_component_cost(self, product):
        """Costo de un componente del kit: precio del primer proveedor del
        producto (por orden de secuencia en su lista de precios de compra),
        convertido a la moneda de la compañía (TRM x 1.05 si la moneda del
        proveedor difiere) y multiplicado por su factor de importación —
        la misma fórmula de exwork que usa price_list_sales para las líneas
        de venta normales, sin la rentabilidad (esto es costo, no precio
        de venta)."""
        self.ensure_one()
        seller = product.seller_ids[:1]
        if not seller:
            return 0.0

        company = self.company_id or self.env.company
        company_currency = company.currency_id
        seller_currency = seller.currency_id

        if seller_currency and seller_currency != company_currency:
            trm = self.env['res.currency']._get_conversion_rate(
                seller_currency, company_currency, company,
                fields.Date.context_today(self),
            )
            exwork = seller.price * trm * 1.05
        else:
            exwork = seller.price

        return exwork * (seller.factor_importacion or 1)

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
            # Sin esto, la línea nueva nace con la secuencia por defecto (10)
            # y empata con líneas ya existentes, desordenando su posición
            # relativa (sale.order.line ordena por order_id, sequence, id).
            last_sequence = max(order.order_line.mapped('sequence') or [0])
            kit_line = self.env['sale.order.line'].create({
                'order_id': order.id,
                'product_id': product.id,
                'product_uom_id': product.uom_id.id,
                'product_uom_qty': 1.0,
                'price_unit': product.lst_price,
                'sequence': last_sequence + 10,
            })
            kit_line._create_kit_component_lines()


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    component_unit_cost = fields.Float(
        string="Costo EXW",
        compute='_compute_component_cost',
        help="Costo unitario de este componente: precio del primer proveedor "
             "del producto convertido a la moneda de la compañía y con su "
             "factor de importación aplicado (misma fórmula de exwork que "
             "usa price_list_sales; ver mrp.bom._get_component_cost).",
    )
    component_cost = fields.Float(
        string="Costo Total EXW",
        compute='_compute_component_cost',
        help="Costo de este componente (costo unitario x cantidad). La suma "
             "de esta columna es el costo total del kit.",
    )

    @api.depends('product_id', 'product_qty')
    def _compute_component_cost(self):
        for line in self:
            unit_cost = line.bom_id._get_component_cost(line.product_id)
            line.component_unit_cost = unit_cost
            line.component_cost = unit_cost * line.product_qty
