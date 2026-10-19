# -*- coding: utf-8 -*-
from odoo import api, models

# Solo las cuentas cuyo código comienza con alguno de estos dígitos
# (ingresos, gastos, costos en el PUC colombiano) reciben la distribución
# analítica del contacto en los apuntes contables -son las cuentas propias
# de las líneas de producto de la factura-. El resto (cuentas por
# cobrar/pagar, impuestos, retenciones, etc.) queda sin distribución.
ANALYTIC_ACCOUNT_CODE_PREFIXES = ('4', '5', '6')


class ResPartner(models.Model):
    _inherit = ['res.partner', 'analytic.mixin']


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.onchange('partner_id')
    def _onchange_partner_id_recompute_analytic_distribution(self):
        self.order_line._compute_analytic_distribution()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('order_id.partner_id.analytic_distribution')
    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        for line in self:
            partner_distribution = line.order_id.partner_id.analytic_distribution
            if not line.display_type and partner_distribution:
                line.analytic_distribution = partner_distribution


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.onchange('partner_id')
    def _onchange_partner_id_recompute_analytic_distribution(self):
        self.order_line._compute_analytic_distribution()

    def _update_analytic_distribution(self):
        # La distribución analítica del proveedor (si está configurada)
        # tiene prioridad sobre la del almacén (`default_account_analytic_id`,
        # definida en `analytic_account_subscorp`); en ese caso la aplica
        # `PurchaseOrderLine._compute_analytic_distribution` y no hay que
        # sobreescribirla aquí.
        self.ensure_one()
        if self.partner_id.analytic_distribution:
            return
        return super()._update_analytic_distribution()


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.depends('order_id.partner_id.analytic_distribution')
    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        for line in self:
            partner_distribution = line.order_id.partner_id.analytic_distribution
            if not line.display_type and partner_distribution:
                line.analytic_distribution = partner_distribution


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.onchange('partner_id')
    def _onchange_partner_id_recompute_analytic_distribution(self):
        self.invoice_line_ids._compute_analytic_distribution()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.onchange('account_id')
    def _onchange_account_id_recompute_analytic_distribution(self):
        self._compute_analytic_distribution()

    @api.depends('partner_id.analytic_distribution', 'account_id')
    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        for line in self:
            if line.display_type != 'product':
                continue
            account_code = line.account_id.code or ''
            if not account_code.startswith(ANALYTIC_ACCOUNT_CODE_PREFIXES):
                # Fuera de ingresos/gastos/costos (4, 5, 6) -cuentas por
                # cobrar/pagar, impuestos, activos, etc.- nunca debe quedar
                # la distribución analítica del contacto: se limpia
                # explícitamente, incluso si ya la tenía de un cambio de
                # cuenta anterior.
                line.analytic_distribution = False
                continue
            partner_distribution = line.partner_id.analytic_distribution
            if partner_distribution:
                line.analytic_distribution = partner_distribution
