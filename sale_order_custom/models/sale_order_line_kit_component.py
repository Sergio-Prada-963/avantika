# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # Un `domain` puesto solo en la vista (arch) NO oculta registros ya
    # existentes de un one2many -- eso solo filtra el diálogo de
    # "buscar/crear". Para que `order_line` de verdad excluya las líneas
    # técnicas de componentes de kit en cualquier lugar donde se lea
    # (formulario, reportes, portal, etc.), el dominio tiene que ir en la
    # propia definición Python del campo.
    order_line = fields.One2many(
        "sale.order.line", "order_id",
        domain=[("is_kit_component_line", "=", False)],
    )


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    kit_line_id = fields.Many2one(
        "sale.order.line",
        string="Línea de Kit de Origen",
        ondelete="cascade",
        index=True,
        help="Si esta línea es un componente técnico de un kit (no se "
             "muestra en la orden de venta ni se entrega/factura por "
             "separado), apunta a la línea del kit que la generó. Se borra "
             "en cascada si se borra la línea del kit.",
    )
    kit_component_line_ids = fields.One2many(
        "sale.order.line", "kit_line_id",
        string="Líneas de Componentes del Kit",
    )
    is_kit_component_line = fields.Boolean(
        string="Es Componente Técnico de Kit",
        help="Línea técnica creada automáticamente por cada componente de "
             "un kit, solo para seguimiento de compra (Compra por Demanda). "
             "Se mantiene con product_uom_qty = 0 a propósito para que no "
             "dispare entrega ni facturación; la cantidad real a comprar "
             "vive en kit_component_qty.",
    )
    kit_component_qty = fields.Float(
        string="Cantidad del Componente",
        digits="Product Unit",
        help="Cantidad de este componente necesaria para fabricar/armar la "
             "cantidad de kits vendida en la línea de origen.",
    )

    def _create_kit_component_lines(self):
        """Crea, para cada línea de kit en `self`, una línea técnica por
        cada componente de su lista de materiales (ver `is_kit_component_line`).
        Se llama justo después de crear la línea del kit."""
        for line in self:
            bom = line._get_kit_bom()
            if not bom or not bom.product_qty:
                continue
            for bom_line in bom.bom_line_ids:
                component_qty = bom_line.product_qty * line.product_uom_qty / bom.product_qty
                self.create({
                    "order_id": line.order_id.id,
                    "product_id": bom_line.product_id.id,
                    "product_uom_id": bom_line.product_id.uom_id.id,
                    "product_uom_qty": 0.0,
                    "price_unit": 0.0,
                    "kit_line_id": line.id,
                    "is_kit_component_line": True,
                    "kit_component_qty": component_qty,
                    # Sin esto nace con la secuencia por defecto (10) y
                    # empata con otras líneas de la misma orden, desordenando
                    # su posición relativa al ordenar por (sequence, id).
                    "sequence": line.sequence #deberia colocar 9999999,
                })

    def write(self, vals):
        result = super().write(vals)
        if "product_uom_qty" in vals:
            for line in self:
                if line.is_kit_component_line or not line.kit_component_line_ids:
                    continue
                bom = line._get_kit_bom()
                if not bom or not bom.product_qty:
                    continue
                for component in line.kit_component_line_ids:
                    bom_line = bom.bom_line_ids.filtered(
                        lambda bl: bl.product_id == component.product_id
                    )[:1]
                    if bom_line:
                        component.kit_component_qty = (
                            bom_line.product_qty * line.product_uom_qty / bom.product_qty
                        )
        return result

    def _get_order_lines_to_report(self):
        lines = super()._get_order_lines_to_report()
        return lines.filtered(lambda line: not line.is_kit_component_line)

    @api.depends('is_kit_component_line')
    def _compute_price_unit(self):
        # Dependencia del mismo modelo (sale.order.line), segura para el
        # precompute de `price_unit` en el core. Se fuerza el precio a 0
        # DESPUÉS de la cadena normal (price_list_sales, AIU, etc.) para que
        # estas líneas técnicas nunca muestren ni usen un precio calculado,
        # sin importar qué lógica de lista de precios les aplicaría de otro
        # modo por tener un product_id real.
        super()._compute_price_unit()
        for line in self:
            if line.is_kit_component_line:
                line.price_unit = 0.0
                line.technical_price_unit = 0.0
