# -*- coding: utf-8 -*-
from odoo import _, api, fields, models

AIU_PERCENT_FIELD_BY_LINE_TYPE = {
    'administracion': 'aiu_administracion_percent',
    'imprevistos': 'aiu_imprevistos_percent',
    'utilidades': 'aiu_utilidades_percent',
}


class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_aiu_quotation = fields.Boolean(string="Cotización AIU")
    aiu_administracion_percent = fields.Float(string="Administración")
    aiu_imprevistos_percent = fields.Float(string="Imprevistos")
    aiu_utilidades_percent = fields.Float(string="Utilidades")

    def _get_aiu_line_specs(self):
        self.ensure_one()
        company = self.company_id or self.env.company
        return [
            ('administracion', company.aiu_administracion_product_id),
            ('imprevistos', company.aiu_imprevistos_product_id),
            ('utilidades', company.aiu_utilidades_product_id),
        ]

    @api.onchange('is_aiu_quotation')
    def _onchange_is_aiu_quotation(self):
        self.ensure_one()
        if self.is_aiu_quotation:
            return self._add_aiu_lines()
        self._remove_aiu_lines()

    @api.onchange(
        'aiu_administracion_percent', 'aiu_imprevistos_percent', 'aiu_utilidades_percent',
    )
    def _onchange_aiu_percentages(self):
        self.ensure_one()
        self._recompute_aiu_lines_price()

    @api.onchange('order_line')
    def _onchange_order_line_aiu(self):
        # Cuando se agrega/edita/quita un producto normal cambia la base
        # (suma de subtotales sin AIU), así que hay que recalcular las 3
        # líneas AIU explícitamente: el encadenamiento de dependencias a
        # través de otro modelo (línea -> orden -> %) no es seguro para el
        # precompute de `price_unit` (ver `_compute_price_unit`), así que
        # el recálculo en vivo se hace por completo aquí.
        self.ensure_one()
        self._recompute_aiu_lines_price()

    def _recompute_aiu_lines_price(self):
        self.ensure_one()
        aiu_lines = self.order_line.filtered('aiu_line_type')
        if not aiu_lines:
            return
        base = sum(self.order_line.filtered(
            lambda l: not l.aiu_line_type
        ).mapped('price_subtotal'))
        for line in aiu_lines.with_context(sale_write_from_compute=True):
            percent_field = AIU_PERCENT_FIELD_BY_LINE_TYPE.get(line.aiu_line_type)
            if not percent_field:
                continue
            price = base * self[percent_field]
            line.price_unit = price
            line.technical_price_unit = price

    def write(self, vals):
        result = super().write(vals)
        if 'is_aiu_quotation' in vals:
            for order in self:
                if order.is_aiu_quotation:
                    order._add_aiu_lines()
                else:
                    order.order_line.filtered('aiu_line_type').unlink()
        return result

    def _add_aiu_lines(self):
        self.ensure_one()
        if self.order_line.filtered('aiu_line_type'):
            return

        specs = self._get_aiu_line_specs()
        if any(not product for __, product in specs):
            return {'warning': {
                'title': _("Productos AIU no configurados"),
                'message': _(
                    "Configure los productos de Administración, Imprevistos y "
                    "Utilidades en Ventas > Configuración > Ajustes antes de "
                    "activar la Cotización AIU."
                ),
            }}

        commands = [(0, 0, {
            'display_type': 'line_section',
            'name': _("Costos indirectos"),
            'aiu_line_type': 'section',
            'price_unit': 0.0,
        })]
        for line_type, product in specs:
            commands.append((0, 0, {
                'product_id': product.id,
                'product_uom_qty': 1.0,
                'product_uom_id': product.uom_id.id,
                'aiu_line_type': line_type,
                'price_unit': 0.0,
            }))
        self.order_line = commands
        self._recompute_aiu_lines_price()

    def _remove_aiu_lines(self):
        self.ensure_one()
        aiu_lines = self.order_line.filtered('aiu_line_type')
        if aiu_lines:
            self.order_line -= aiu_lines


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    aiu_line_type = fields.Selection(
        selection=[
            ('section', "Sección AIU"),
            ('administracion', "Administración"),
            ('imprevistos', "Imprevistos"),
            ('utilidades', "Utilidades"),
        ],
        string="Tipo de Línea AIU",
    )

    @api.depends('aiu_line_type')
    def _compute_price_unit(self):
        # OJO: `price_unit` es `precompute=True` en el core (sale.order.line).
        # El precompute solo funciona con dependencias del MISMO modelo; si se
        # agrega aquí una dependencia hacia `sale.order` (p.ej.
        # `order_id.aiu_administracion_percent`), Odoo deja de poder
        # precomputar el campo al crear las líneas y termina insertándolas
        # sin valor en `price_unit`, violando el NOT NULL. Por eso el
        # recálculo en vivo por cambios de % u otras líneas se hace por
        # completo vía onchange (`_recompute_aiu_lines_price` en sale.order),
        # y este compute solo cubre la creación/copia de líneas AIU.
        super()._compute_price_unit()
        for line in self:
            percent_field = AIU_PERCENT_FIELD_BY_LINE_TYPE.get(line.aiu_line_type)
            if not percent_field:
                continue

            order = line.order_id
            base = sum(order.order_line.filtered(
                lambda l: not l.aiu_line_type
            ).mapped('price_subtotal'))
            price = base * order[percent_field]

            line = line.with_context(sale_write_from_compute=True)
            line.price_unit = price
            line.technical_price_unit = price
