# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    can_approve_purchase = fields.Boolean(
        string="Puede Aprobar esta Compra",
        compute='_compute_can_approve_purchase',
        help="Verdadero si el usuario actual es el \"Usuario que Aprueba "
             "Compras\" configurado en Ajustes > Compras para la compañía "
             "de esta orden.",
    )

    show_confirm_button_no_approval = fields.Boolean(
        string="Mostrar Botón de Confirmar sin Aprobación",
        compute='_compute_show_confirm_button_no_approval',
        help="Verdadero si el usuario actual tiene activo el permiso "
             "\"Confirmar Compras sin Aprobación\" en sus preferencias.",
    )

    @api.depends('company_id.purchase_approval_user_id')
    @api.depends_context('uid')
    def _compute_can_approve_purchase(self):
        for order in self:
            order.can_approve_purchase = (
                order.company_id.purchase_approval_user_id == self.env.user
            )

    @api.depends_context('uid')
    def _compute_show_confirm_button_no_approval(self):
        show = self.env.user.show_confirm_button_purchase_no_approval
        for order in self:
            order.show_confirm_button_no_approval = show

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
            'purchase_custom.action_server_purchase_approval_preview'
        )
        return server_action.with_context(
            active_model='purchase.order', active_ids=self.ids,
        ).run()

    def action_approve_from_button(self):
        """Botón "Aprobar" visible en el formulario, solo para el usuario
        configurado como aprobador de compras."""
        self.ensure_one()
        if self.env.user != self.company_id.purchase_approval_user_id:
            raise UserError(_(
                "Solo %s puede aprobar esta orden de compra."
            ) % (self.company_id.purchase_approval_user_id.display_name or _("el aprobador configurado")))
        if self.state != 'to approve':
            raise UserError(_("Solo se puede aprobar una orden que esté en estado \"Por Aprobar\"."))
        self._approve_purchase(_("Orden aprobada y confirmada desde el formulario."))

    def action_confirm_no_approval(self):
        """Botón "Confirmar" visible en el formulario (en Borrador y Por
        Aprobar) solo para usuarios con el permiso "Confirmar Compras sin
        Aprobación" activo, que confirma la orden directamente sin pasar
        por el flujo de aprobación por correo."""
        self.ensure_one()
        if not self.env.user.show_confirm_button_purchase_no_approval:
            raise UserError(_(
                "No tienes permiso para confirmar compras sin aprobación."
            ))
        if self.state not in ('draft', 'to approve'):
            raise UserError(_(
                "Solo se puede confirmar una orden en estado Borrador o Por Aprobar."
            ))
        if self.state == 'draft':
            error_msg = self._confirmation_error_message()
            if error_msg:
                raise UserError(error_msg)
        self._approve_purchase(_(
            "Orden confirmada directamente por %s, sin pasar por el flujo "
            "de aprobación por correo."
        ) % self.env.user.display_name)

    def action_approve_by_email(self):
        """Se ejecuta cuando el aprobador hace clic en el botón "Aprobar" del
        correo (enlace de un clic, sin necesidad de iniciar sesión, ver
        controllers/portal.py)."""
        self.ensure_one()
        if self.state != 'to approve':
            return
        self._approve_purchase(_(
            "Orden aprobada y confirmada mediante el enlace de aprobación enviado por correo."
        ))

    def _approve_purchase(self, log_message):
        self.ensure_one()
        vals = {'state': 'purchase', 'date_approve': fields.Datetime.now()}
        self.sudo().write(vals)
        if self.lock_confirmed_po == 'lock':
            self.sudo().write({'locked': True})
        self.message_post(body=log_message)
