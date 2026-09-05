# -*- coding: utf-8 -*-
from odoo import api, models


class ResPartner(models.Model):
    _inherit = ['res.partner', 'analytic.mixin']


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


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.depends('partner_id.analytic_distribution')
    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        for line in self:
            partner_distribution = line.partner_id.analytic_distribution
            if line.display_type == 'product' and partner_distribution:
                line.analytic_distribution = partner_distribution
