# -*- coding: utf-8 -*-
from odoo import api, models

CUSTOM_INVOICE_MOVE_TYPES = ('out_invoice', 'out_refund')


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _get_default_pdf_report_id(self, move):
        """Para facturas y notas crédito de cliente, usar nuestra propia
        plantilla de factura electrónica en vez del PDF estándar de Odoo,
        salvo que el contacto o el diario ya tengan configurada
        explícitamente otra plantilla -esa configuración explícita siempre
        tiene prioridad."""
        if move.move_type in CUSTOM_INVOICE_MOVE_TYPES:
            has_explicit_override = bool(
                move.commercial_partner_id.with_company(move.company_id).invoice_template_pdf_report_id
                or move.journal_id.with_company(move.company_id).invoice_template_pdf_report_id
            )
            if not has_explicit_override:
                custom_report = self.env.ref(
                    'account_move_custom.action_report_custom_invoice',
                    raise_if_not_found=False,
                )
                if custom_report and move._is_action_report_available(custom_report):
                    return custom_report
        return super()._get_default_pdf_report_id(move)
