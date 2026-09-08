# -*- coding: utf-8 -*-
from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request

from odoo.addons.purchase.controllers.portal import CustomerPortal


class PurchaseApprovalPortal(CustomerPortal):

    @http.route(['/my/purchase/<int:order_id>/approve'], type='http', auth='public')
    def purchase_order_approve_by_email(self, order_id, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('purchase.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if order_sudo.state == 'to approve':
            order_sudo.action_approve_by_email()

        return request.render('purchase_sale_demand.approval_result_page', {
            'order': order_sudo,
        })
