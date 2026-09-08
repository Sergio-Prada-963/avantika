# -*- coding: utf-8 -*-
from odoo import _, models


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    def action_send_mail(self):
        res = super().action_send_mail()
        if self.env.context.get('purchase_approval_flow'):
            for wizard in self:
                if wizard.model != 'purchase.order':
                    continue
                orders = self.env['purchase.order'].browse(wizard._evaluate_res_ids())
                to_approve = orders.filtered(lambda o: o.state == 'draft')
                to_approve.write({'state': 'to approve'})
                for order in to_approve:
                    order.message_post(body=_(
                        "Se envió la orden por correo a %s para su aprobación."
                    ) % (order.company_id.purchase_approval_user_id.display_name or _("el aprobador")))
        return res
