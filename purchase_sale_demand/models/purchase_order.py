# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import formatLang


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_send_for_approval(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Solo se puede enviar a aprobación una orden en borrador."))
        error_msg = self._confirmation_error_message()
        if error_msg:
            raise UserError(error_msg)
        if not self.company_id.purchase_approval_user_id:
            raise UserError(_(
                "Configura un \"Usuario que Aprueba Compras\" en Ajustes > "
                "Compras antes de enviar una orden a aprobación."
            ))
        return {
            'type': 'ir.actions.act_window',
            'name': _("Enviar Aprobación"),
            'res_model': 'purchase.approval.send.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_purchase_order_id': self.id},
        }

    def _get_approval_email_body(self):
        self.ensure_one()
        approval_url = self.get_portal_url(suffix='/approve')
        amount = formatLang(self.env, self.amount_total, currency_obj=self.currency_id)
        return Markup(
            '<p>%s</p>'
            '<p>%s</p>'
            '<p style="text-align:center;margin:24px 0;">'
            '<a href="%s" style="background-color:#875A7B;color:#ffffff;'
            'padding:12px 24px;text-decoration:none;border-radius:5px;'
            'font-weight:bold;display:inline-block;">%s</a>'
            '</p>'
        ) % (
            _("Se solicita tu aprobación para la siguiente orden de compra: %s") % self.name,
            _("Proveedor: %(partner)s — Total: %(amount)s") % {
                'partner': self.partner_id.display_name,
                'amount': amount,
            },
            approval_url,
            _("Aprobar y Confirmar Compra"),
        )

    def action_approve_by_email(self):
        self.ensure_one()
        if self.state != 'to approve':
            return
        vals = {'state': 'purchase', 'date_approve': fields.Datetime.now()}
        self.sudo().write(vals)
        if self.lock_confirmed_po == 'lock':
            self.sudo().write({'locked': True})
        self.message_post(body=_(
            "Orden aprobada y confirmada mediante el enlace de aprobación enviado por correo."
        ))
