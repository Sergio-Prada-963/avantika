# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrderChangeCustomerWizard(models.TransientModel):
    _name = 'sale.order.change.customer.wizard'
    _description = 'Cambiar Cliente de la Orden de Venta'

    order_id = fields.Many2one('sale.order', required=True)
    current_partner_id = fields.Many2one(
        related='order_id.partner_id', string="Cliente Actual", readonly=True,
    )
    new_partner_id = fields.Many2one(
        'res.partner', string="Nuevo Cliente", required=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'order_id' in fields_list and not res.get('order_id'):
            res['order_id'] = self.env.context.get('active_id')
        return res

    def _get_customer_change_message(self, old_partner, new_partner, doc_label):
        template = _(
            "Se cambió el cliente de %(old)s a %(new)s en %(doc)s, por un "
            "cambio de cliente realizado desde la orden de venta %(sale_order)s."
        )
        return Markup(template) % {
            'old': Markup(
                '<span style="color:#dc3545;text-decoration:line-through;">%s</span>'
            ) % old_partner.display_name,
            'new': Markup(
                '<span style="color:#28a745;font-weight:bold;">%s</span>'
            ) % new_partner.display_name,
            'doc': doc_label,
            'sale_order': self.order_id.display_name,
        }

    def _change_invoices(self, invoices, old_partner, new_partner):
        # Una factura ya validada (o cancelada) no se toca: cambiar el
        # cliente de un documento contable ya emitido (más aún con
        # facturación electrónica DIAN de por medio) puede ser ilegal, no
        # solo inconveniente. Solo se actualizan las que siguen en borrador.
        updatable = invoices.filtered(lambda m: m.state == 'draft')
        skipped = invoices - updatable
        for move in updatable:
            move.partner_id = new_partner.id
        for move in updatable:
            move.message_post(
                body=self._get_customer_change_message(old_partner, new_partner, _("esta factura"))
            )
        return updatable, skipped

    def _change_pickings(self, pickings, old_partner, new_partner):
        updatable = pickings.filtered(lambda p: p.state not in ('done', 'cancel'))
        skipped = pickings - updatable
        for picking in updatable:
            picking.partner_id = new_partner.id
        for picking in updatable:
            picking.message_post(
                body=self._get_customer_change_message(old_partner, new_partner, _("esta entrega"))
            )
        return updatable, skipped

    def action_change_customer(self):
        self.ensure_one()
        order = self.order_id
        new_partner = self.new_partner_id
        old_partner = order.partner_id
        if old_partner == new_partner:
            raise UserError(_("El cliente seleccionado es el mismo que ya tiene la orden."))

        # La dirección de facturación/entrega solo se actualiza si seguía
        # siendo la misma que el cliente principal (es decir, si nadie la
        # había cambiado a propósito a un contacto distinto).
        vals = {'partner_id': new_partner.id}
        if order.partner_invoice_id == old_partner:
            vals['partner_invoice_id'] = new_partner.id
        if order.partner_shipping_id == old_partner:
            vals['partner_shipping_id'] = new_partner.id
        order.write(vals)

        updated_invoices, skipped_invoices = self._change_invoices(
            order.invoice_ids, old_partner, new_partner
        )
        updated_pickings, skipped_pickings = self._change_pickings(
            order.picking_ids, old_partner, new_partner
        )

        old_html = Markup(
            '<span style="color:#dc3545;text-decoration:line-through;">%s</span>'
        ) % old_partner.display_name
        new_html = Markup(
            '<span style="color:#28a745;font-weight:bold;">%s</span>'
        ) % new_partner.display_name

        message = Markup(_("Cliente cambiado de %(old)s a %(new)s.")) % {
            'old': old_html, 'new': new_html,
        }
        if updated_invoices:
            message += Markup('<br/>') + Markup(_(
                "Se actualizó el cliente en %(count)s factura(s) en borrador relacionada(s)."
            )) % {'count': len(updated_invoices)}
        if skipped_invoices:
            message += Markup('<br/>') + Markup(_(
                "No se pudo actualizar %(count)s factura(s) relacionada(s) "
                "(ya están validadas o canceladas)."
            )) % {'count': len(skipped_invoices)}
        if updated_pickings:
            message += Markup('<br/>') + Markup(_(
                "Se actualizó el cliente en %(count)s entrega(s) relacionada(s)."
            )) % {'count': len(updated_pickings)}
        if skipped_pickings:
            message += Markup('<br/>') + Markup(_(
                "No se pudo actualizar %(count)s entrega(s) relacionada(s) "
                "(ya están hechas o canceladas)."
            )) % {'count': len(skipped_pickings)}
        order.message_post(body=message)

        return {'type': 'ir.actions.act_window_close'}
