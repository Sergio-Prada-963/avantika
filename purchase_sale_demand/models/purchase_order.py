# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


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
        server_action = self.env.ref(
            'purchase_sale_demand.action_server_purchase_approval_preview'
        )
        return server_action.with_context(
            active_model='purchase.order', active_ids=self.ids,
        ).run()

    def action_approve_by_email(self):
        """Se ejecuta cuando el aprobador hace clic en el botón "Aprobar" del
        correo (enlace de un clic, sin necesidad de iniciar sesión, ver
        controllers/portal.py)."""
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
