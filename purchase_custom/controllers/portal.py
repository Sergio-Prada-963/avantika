# -*- coding: utf-8 -*-
from odoo import http
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request

from odoo.addons.purchase.controllers.portal import CustomerPortal


class PurchaseApprovalPortal(CustomerPortal):

    @http.route(['/my/purchase/<int:order_id>/approve'], type='http', auth='user')
    def purchase_order_approve_by_email(self, order_id, access_token=None, **kw):
        # `auth='user'` obliga a iniciar sesión antes de llegar aquí (si no
        # hay sesión, Odoo redirige solo a /web/login y regresa después).
        # Esto es necesario porque validamos la identidad real contra el
        # aprobador configurado; el enlace/token del correo, por sí solo,
        # no prueba quién es la persona que hizo click.
        #
        # OJO: se guarda `request.env.user` ANTES de llamar a
        # `_document_check_access`, porque ese método (del core, portal)
        # devuelve el registro con `with_user(SUPERUSER_ID)` aplicado
        # internamente -- `order_sudo.env.user` sería siempre OdooBot, sin
        # importar quién esté realmente logueado.
        approving_user = request.env.user

        try:
            order_sudo = self._document_check_access('purchase.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        error_message = False
        if order_sudo.state == 'to approve':
            try:
                order_sudo.action_approve_by_email(approving_user)
            except UserError as exc:
                error_message = str(exc)

        return request.render('purchase_custom.approval_result_page', {
            'order': order_sudo,
            'error_message': error_message,
            'rejected': False,
        })

    @http.route(['/my/purchase/<int:order_id>/reject'], type='http', auth='user')
    def purchase_order_reject_by_email(self, order_id, access_token=None, **kw):
        # Mismo mecanismo que /approve (ver comentarios ahí): se guarda el
        # usuario real ANTES de `_document_check_access`, que devuelve el
        # registro con `with_user(SUPERUSER_ID)`.
        rejecting_user = request.env.user

        try:
            order_sudo = self._document_check_access('purchase.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        error_message = False
        rejected = False
        if order_sudo.state == 'to approve':
            try:
                order_sudo.action_reject_by_email(rejecting_user)
                rejected = True
            except UserError as exc:
                error_message = str(exc)

        return request.render('purchase_custom.approval_result_page', {
            'order': order_sudo,
            'error_message': error_message,
            'rejected': rejected,
        })
