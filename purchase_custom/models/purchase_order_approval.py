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

    def action_approve_by_email(self, approving_user):
        """Se ejecuta cuando el aprobador hace clic en el botón "Aprobar" del
        correo (enlace de un clic). `approving_user` debe ser el usuario
        REAL de la sesión (`request.env.user` en controllers/portal.py), NO
        `self.env.user`: el registro que llega aquí (`order_sudo`, devuelto
        por `_document_check_access`) viene con `with_user(SUPERUSER_ID)`
        aplicado internamente por el core, así que `self.env.user` sería
        siempre OdooBot sin importar quién esté logueado."""
        self.ensure_one()
        if self.state != 'to approve':
            return
        if approving_user != self.company_id.purchase_approval_user_id:
            raise UserError(_(
                "Solo %s puede aprobar esta orden de compra."
            ) % (self.company_id.purchase_approval_user_id.display_name or _("el aprobador configurado")))
        self._approve_purchase(_(
            "Orden aprobada y confirmada mediante el enlace de aprobación enviado por correo."
        ))

    def action_reject_by_email(self, rejecting_user):
        """Se ejecuta cuando el aprobador hace clic en el botón "Rechazar" del
        correo (mismo mecanismo de un clic que "Aprobar"): cancela la orden
        vía el método nativo `button_cancel()` y notifica al comprador
        (`user_id`) por el chatter, sin salir del correo."""
        self.ensure_one()
        if self.state != 'to approve':
            return
        if rejecting_user != self.company_id.purchase_approval_user_id:
            raise UserError(_(
                "Solo %s puede rechazar esta orden de compra."
            ) % (self.company_id.purchase_approval_user_id.display_name or _("el aprobador configurado")))
        self.sudo().with_context(purchase_reject_notified=True).button_cancel()
        comprador = self.user_id
        self.message_post(
            body=_(
                "Orden rechazada por %s mediante el enlace de rechazo enviado por correo."
            ) % rejecting_user.display_name,
            partner_ids=comprador.partner_id.ids if comprador else False,
        )

    def button_cancel(self):
        # Si se cancela mientras está "Por Aprobar", es efectivamente un
        # rechazo de la aprobación: se notifica al comprador (`user_id`) por
        # el chatter. Cubre tanto el botón nativo "Cancelar" del formulario
        # como cualquier otro camino que llame a este método; se salta si
        # `action_reject_by_email` ya lo llamó (ese método publica su propio
        # mensaje, más detallado, para no duplicar la notificación).
        orders_to_notify = self.filtered(
            lambda o: o.state == 'to approve'
        ) if not self.env.context.get('purchase_reject_notified') else self.browse()
        result = super().button_cancel()
        for order in orders_to_notify:
            comprador = order.user_id
            order.message_post(
                body=_("La aprobación de esta orden de compra fue rechazada."),
                partner_ids=comprador.partner_id.ids if comprador else False,
            )
        return result

    def _approval_allowed(self):
        # El flujo de aprobación por correo/botones de este módulo es un
        # camino alterno y deliberado al de doble validación nativo (los
        # botones nativos están ocultos en la vista): un aprobador designado
        # aquí puede no cumplir las reglas nativas de _approval_allowed()
        # (grupo de compras o monto por debajo del umbral). Este contexto
        # se activa solo desde `_approve_purchase`, después de validar la
        # identidad correcta en cada método `action_*` de este archivo.
        return (
            super()._approval_allowed()
            or bool(self.env.context.get('purchase_custom_force_approve'))
        )

    def _approve_purchase(self, log_message):
        self.ensure_one()
        # Se llama al método nativo `button_approve()` (en vez de escribir
        # el estado a mano) para que se ejecuten todos sus efectos
        # secundarios normales: por ejemplo `purchase_stock` crea ahí mismo
        # la recepción (picking) de la compra. Escribir el estado
        # directamente los saltaba por completo.
        self.sudo().with_context(purchase_custom_force_approve=True).button_approve()
        self.message_post(body=log_message)
