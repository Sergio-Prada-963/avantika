# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseApprovalSendWizard(models.TransientModel):
    _name = 'purchase.approval.send.wizard'
    _description = "Enviar Aprobación de Compra por Correo"

    purchase_order_id = fields.Many2one(
        'purchase.order', string="Orden de Compra", required=True, readonly=True,
    )
    partner_id = fields.Many2one(
        'res.partner', string="Destinatario", required=True,
    )
    subject = fields.Char(required=True)
    body = fields.Html(required=True, sanitize=False)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        order = self.env['purchase.order'].browse(res.get('purchase_order_id'))
        if order:
            approver = order.company_id.purchase_approval_user_id
            if 'partner_id' in fields_list:
                res.setdefault('partner_id', approver.partner_id.id)
            if 'subject' in fields_list:
                res.setdefault('subject', _("Aprobación requerida: Orden de Compra %s") % order.name)
            if 'body' in fields_list:
                res.setdefault('body', order._get_approval_email_body())
        return res

    def action_send(self):
        self.ensure_one()
        order = self.purchase_order_id
        if not self.partner_id.email:
            raise UserError(_("El destinatario seleccionado no tiene un correo configurado."))

        self.env['mail.mail'].sudo().create({
            'subject': self.subject,
            'body_html': self.body,
            'email_to': self.partner_id.email,
            'auto_delete': True,
        }).send()

        order.write({'state': 'to approve'})
        order.message_post(body=_(
            "Se envió la orden a %s para su aprobación por correo."
        ) % self.partner_id.display_name)
        return {'type': 'ir.actions.act_window_close'}
