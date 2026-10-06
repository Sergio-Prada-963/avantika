# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError

DEMAND_INDICATOR_SELECTION = [
    ('verde', "Verde"),
    ('amarillo', "Amarillo"),
    ('rojo', "Rojo"),
    ('negro', "Negro"),
]


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    purchase_line_ids = fields.One2many(
        'purchase.order.line', 'sale_line_id',
        string="Líneas de Compra",
    )
    kit_product_id = fields.Many2one(
        'product.product',
        string="Producto del Kit",
        related='kit_line_id.product_id',
        store=True,
        help="Si esta línea es un componente técnico de un kit, el "
             "producto del kit que la generó.",
    )
    product_brand = fields.Char(
        string="Marca",
        related='product_id.product_tmpl_id.l10n_co_edi_brand',
        store=True,
    )
    order_tag_ids = fields.Many2many(
        'crm.tag',
        string="Etiquetas",
        related='order_id.tag_ids',
    )
    purchase_proveedor_id = fields.Many2one(
        'res.partner',
        string="Proveedor de Compra",
        related='supplierinfo_id.partner_id',
        store=True,
        help="Proveedor del ítem de la lista de precios de venta; si la "
             "línea no encontró ninguno, se usa el primer proveedor de la "
             "lista de precios de compra del producto (campo "
             "supplierinfo_id de price_list_sales).",
    )
    purchase_currency_id = fields.Many2one(
        'res.currency',
        string="Moneda Proveedor",
        compute='_compute_purchase_currency_id',
    )
    product_qty_available = fields.Float(
        string="Cantidad Disponible en Inventario",
        compute='_compute_product_qty_available',
        help="Disponible en general del producto, sumando TODAS las "
             "ubicaciones internas de todas las bodegas/compañías "
             "permitidas, neto de lo ya reservado (de cualquier línea). "
             "Calculado directo desde stock.quant, sin depender de "
             "qty_available/free_qty/virtual_available del producto.",
    )
    qty_reserved_delivery = fields.Float(
        string="Cantidad Reservada para el Pedido",
        compute='_compute_qty_reserved_delivery',
        store=True,
        digits='Product Unit',
    )
    qty_purchased = fields.Float(
        string="Cantidad Comprada",
        compute='_compute_qty_purchased',
        store=True,
        digits='Product Unit',
    )
    qty_to_purchase = fields.Float(
        string="Cantidad a Comprar",
        compute='_compute_qty_to_purchase',
        store=True,
        digits='Product Unit',
    )
    last_purchase_order_state = fields.Selection(
        selection=lambda self: self.env['purchase.order']._fields['state'].selection,
        string="Estado Última Compra",
        compute='_compute_last_purchase_order_state',
        store=True,
    )
    already_purchased = fields.Boolean(
        string="Ya fue Comprado",
        help="Marca esta línea como ya comprada para que deje de aparecer "
             "en el listado de Compra por Demanda, aunque todavía tenga "
             "cantidad pendiente por comprar. Al marcar/desmarcar esta "
             "casilla en la orden de venta se marca/desmarca en todas sus "
             "líneas; y en sentido contrario, la orden queda marcada solo "
             "cuando TODAS sus líneas están marcadas (ver `already_purchased` "
             "en sale.order, compute + inverse).",
    )
    demand_indicator = fields.Selection(
        DEMAND_INDICATOR_SELECTION,
        string="Indicador de Días",
        compute='_compute_demand_indicator',
        store=True,
        help="Semáforo según los días transcurridos entre la fecha de la "
             "orden de venta y hoy, comparado contra los umbrales "
             "configurados en Compras > Configuración > Ajustes. Se "
             "recalcula al cambiar la fecha de la orden o la configuración, "
             "y todos los días vía la acción planificada (solo para líneas "
             "que aún tienen cantidad pendiente por comprar).",
    )
    demand_days = fields.Integer(
        string="Días",
        compute='_compute_demand_indicator',
        store=True,
        aggregator=None,
        help="Días transcurridos entre la fecha de la orden de venta y hoy; "
             "es el número que se muestra en la columna Indicador (coloreada "
             "según demand_indicator). Sin agregador: sumar días entre "
             "líneas no tiene sentido y además rompe el ancho del nombre "
             "del grupo al agrupar por otra columna (p. ej. Proveedor).",
    )
    buyer_id = fields.Many2one(
        'res.users',
        string="Comprador",
        related='purchase_proveedor_id.buyer_id',
        store=True,
    )
    order_delivery_city = fields.Char(
        string="Ciudad de Entrega",
        related='order_id.partner_shipping_id.city',
        store=True,
    )

    @api.depends(
        'order_id.date_order',
        'company_id.indicador_verde',
        'company_id.indicador_amarillo',
        'company_id.indicador_rojo',
        'company_id.indicador_negro',
    )
    def _compute_demand_indicator(self):
        today = fields.Date.context_today(self)
        for line in self:
            date_order = line.order_id.date_order
            if not date_order:
                line.demand_indicator = False
                line.demand_days = 0
                continue

            days = (today - date_order.date()).days
            company = line.company_id or self.env.company

            if days <= company.indicador_verde:
                indicator = 'verde'
            elif days <= company.indicador_amarillo:
                indicator = 'amarillo'
            elif days <= company.indicador_rojo:
                indicator = 'rojo'
            else:
                indicator = 'negro'
            line.demand_indicator = indicator
            line.demand_days = days

    @api.model
    def _cron_recompute_demand_indicator(self):
        lines = self.search([
            ('display_type', '=', False),
            ('qty_to_purchase', '>', 0),
        ])
        lines._compute_demand_indicator()

    @api.model
    def retrieve_demand_dashboard(self, domain=None):
        """Cantidad de líneas pendientes por comprar agrupadas por
        `demand_indicator`, para las cajas de resumen sobre el listado de
        Compra por Demanda. Devuelve conteos "global" (todas) y "my" (solo
        las cuyo proveedor resuelto tiene como "Comprador" (buyer_id) al
        usuario actual).

        `domain` es el dominio actual y completo de la vista (ya incluye el
        domain base de la acción más los filtros/búsqueda que el usuario
        tenga aplicados), para que las cajas cuenten exactamente los
        registros que se están viendo en ese momento. No se le agrega
        ninguna condición extra aquí: si se quita el filtro "Pendientes por
        Comprar", el dashboard también deja de exigirlo."""
        def count_by_indicator(domain):
            groups = self._read_group(domain, ['demand_indicator'], ['__count'])
            counts = {key: 0 for key, _label in self._fields['demand_indicator'].selection}
            for indicator, count in groups:
                if indicator:
                    counts[indicator] = count
            return counts

        domain = domain or []
        my_domain = domain + [('purchase_proveedor_id.buyer_id', '=', self.env.uid)]
        return {
            'global': count_by_indicator(domain),
            'my': count_by_indicator(my_domain),
        }

    @api.depends('purchase_line_ids.order_id.state', 'purchase_line_ids.order_id.create_date')
    def _compute_last_purchase_order_state(self):
        for line in self:
            last_order = line.purchase_line_ids.mapped('order_id').sorted(
                key=lambda o: o.create_date, reverse=True
            )[:1]
            line.last_purchase_order_state = last_order.state if last_order else False

    @api.depends('supplierinfo_id.currency_id')
    def _compute_purchase_currency_id(self):
        for line in self:
            line.purchase_currency_id = line.supplierinfo_id.currency_id

    @api.depends('product_id.qty_available', 'product_id.free_qty')
    def _compute_product_qty_available(self):
        # Fórmula propia (no delega el VALOR a qty_available/free_qty del
        # producto): suma directamente los stock.quant del producto en
        # todas las ubicaciones internas de todas las bodegas/compañías
        # permitidas, y resta lo ya reservado de
        # esos mismos quants. Se depende de qty_available/free_qty del
        # producto SOLO como disparador (son los campos que Odoo invalida
        # cada vez que cambia algo en stock.quant/stock.move), no se usa su
        # valor en el cálculo.
        for line in self:
            if not line.product_id:
                line.product_qty_available = 0.0
                continue
            quants = self.env['stock.quant'].search([
                ('product_id', '=', line.product_id.id),
                ('location_id.usage', '=', 'internal'),
                ('company_id', 'in', self.env.companies.ids),
            ])
            on_hand = sum(quants.mapped('quantity'))
            reserved = sum(quants.mapped('reserved_quantity'))
            line.product_qty_available = on_hand - reserved

    @api.depends(
        'move_ids.state',
        'move_ids.picked',
        'move_ids.picking_code',
        'move_ids.quantity',
    )
    def _compute_qty_reserved_delivery(self):
        for line in self:
            moves = line.move_ids.filtered(
                lambda m: m.picking_code == 'outgoing'
                and m.state in ('assigned', 'partially_available')
                and not m.picked
            )
            line.qty_reserved_delivery = sum(moves.mapped('quantity'))

    @api.depends(
        'purchase_line_ids.product_qty',
        'purchase_line_ids.order_id.state',
    )
    def _compute_qty_purchased(self):
        for line in self:
            confirmed_lines = line.purchase_line_ids.filtered(
                lambda l: l.order_id.state in ('purchase', 'done')
            )
            line.qty_purchased = sum(confirmed_lines.mapped('product_qty'))

    @api.depends(
        'product_uom_qty', 'qty_reserved_delivery', 'product_qty_available',
        'purchase_line_ids.product_qty', 'purchase_line_ids.qty_received',
        'purchase_line_ids.order_id.state',
        'is_kit_component_line', 'kit_component_qty',
    )
    def _compute_qty_to_purchase(self):
        # product_qty_available es un total GLOBAL del producto, compartido
        # por TODAS las órdenes de venta que lo piden - no es exclusivo de
        # una sola línea. Si cada línea lo restara de forma independiente,
        # varias órdenes del mismo producto podrían mostrar "0 a comprar"
        # simultáneamente aunque, sumadas, la demanda real supere por mucho
        # lo que hay libre (ese disponible se "prestaría" a todas a la vez,
        # cuando en la realidad solo alcanza para una).
        #
        # Para evitarlo se agrupan TODAS las líneas de venta confirmadas que
        # compiten por el mismo producto (no solo las de `self`: Odoo puede
        # recomputar una sola línea sin sus hermanas, así que hay que
        # buscarlas explícitamente) y se reparte el disponible compartido de
        # forma secuencial: FIFO por fecha de confirmación de la orden (la
        # más antigua se queda primero con lo que necesite del disponible
        # compartido; las siguientes solo ven lo que sobra).
        qty_to_purchase_by_line_id = {}
        for product in self.mapped('product_id'):
            competing_lines = self.env['sale.order.line'].search([
                ('product_id', '=', product.id),
                ('display_type', '=', False),
                ('kit_component_line_ids', '=', False),
                ('order_id.state', '=', 'sale'),
                ('already_purchased', '=', False),
            ])
            competing_lines = competing_lines.sorted(
                key=lambda l: (l.order_id.date_order or l.create_date, l.id)
            )
            remaining_pool = competing_lines[:1].product_qty_available if competing_lines else 0.0
            for line in competing_lines:
                base_qty = line.kit_component_qty if line.is_kit_component_line else line.product_uom_qty
                # De lo ya comprado (purchase_line_ids confirmadas) solo se
                # resta la parte que AÚN NO ha llegado (product_qty -
                # qty_received): en cuanto una compra se recibe, esas
                # unidades pasan a ser stock físico y ya quedan cubiertas
                # por product_qty_available/qty_reserved_delivery - restar
                # también qty_purchased completo ahí las contaría dos veces.
                confirmed_purchase_lines = line.purchase_line_ids.filtered(
                    lambda l: l.order_id.state in ('purchase', 'done')
                )
                qty_purchased_pending = sum(
                    max(l.product_qty - l.qty_received, 0.0) for l in confirmed_purchase_lines
                )
                local_remaining = max(
                    base_qty - line.qty_reserved_delivery - qty_purchased_pending,
                    0.0,
                )
                claimed_from_pool = min(local_remaining, remaining_pool)
                remaining_pool -= claimed_from_pool
                qty_to_purchase_by_line_id[line.id] = local_remaining - claimed_from_pool

        for line in self:
            line.qty_to_purchase = qty_to_purchase_by_line_id.get(line.id, 0.0)

    def action_create_purchase_orders(self):
        lines = self.filtered(
            lambda l: not l.display_type and not l.is_downpayment
            and not l.kit_component_line_ids and l.qty_to_purchase > 0
        )
        if not lines:
            raise UserError(_(
                "Selecciona al menos una línea de venta con cantidad "
                "pendiente por comprar."
            ))

        missing_provider = lines.filtered(lambda l: not l.purchase_proveedor_id)
        if missing_provider:
            raise UserError(_(
                "Las siguientes líneas no tienen ningún proveedor definido "
                "(ni en la lista de precios de venta, ni en la lista de "
                "precios de compra del producto); no se puede generar la "
                "compra: %s"
            ) % ', '.join(missing_provider.mapped(lambda l: l.product_id.display_name or l.name)))

        groups = defaultdict(lambda: self.env['sale.order.line'])
        for line in lines:
            groups[line.purchase_proveedor_id] |= line

        purchase_orders = self.env['purchase.order']
        for proveedor, group_lines in groups.items():
            new_lines_vals = [
                (0, 0, {
                    'product_id': line.product_id.id,
                    'product_qty': line.qty_to_purchase,
                    'product_uom_id': line.product_uom_id.id,
                    'sale_line_id': line.id,
                })
                for line in group_lines
            ]

            existing_purchase_order = self.env['purchase.order'].search([
                ('partner_id', '=', proveedor.id),
                ('state', '=', 'draft'),
            ], limit=1)

            if existing_purchase_order:
                existing_purchase_order.write({'order_line': new_lines_vals})
                purchase_orders |= existing_purchase_order
            else:
                purchase_order = self.env['purchase.order'].create({
                    'partner_id': proveedor.id,
                    'order_line': new_lines_vals,
                })
                purchase_orders |= purchase_order

        return {
            'type': 'ir.actions.act_window',
            'name': _("Órdenes de Compra Creadas"),
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', purchase_orders.ids)],
        }
