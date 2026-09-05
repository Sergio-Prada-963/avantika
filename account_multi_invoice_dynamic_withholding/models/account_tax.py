# -*- coding: utf-8 -*-
from odoo import api, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.model
    def _get_withholding_candidate_taxes(self, company, move_type, already_applied_taxes=None):
        """Impuestos candidatos a ser aplicados como retención dinámica en el
        wizard de pago multifactura.

        Combina como UNIÓN los impuestos marcados por cualquiera de los
        mecanismos de clasificación de retención presentes en la base de
        datos (nativo Odoo, DIAN/Enterprise, taxonomía custom del cliente, o
        la convención genérica de "amount negativo"), de forma que un
        impuesto mal clasificado en una sola taxonomía igual aparezca como
        candidato.
        """
        type_tax_use = 'purchase' if move_type in ('in_invoice', 'in_refund', 'in_receipt') else 'sale'
        domain = [
            *self.env['account.tax']._check_company_domain(company),
            ('type_tax_use', '=', type_tax_use),
        ]
        base_taxes = self.search(domain)

        candidates = self.env['account.tax']
        if 'is_withholding_tax_on_payment' in base_taxes._fields:
            candidates |= base_taxes.filtered('is_withholding_tax_on_payment')
        if 'l10n_co_edi_type' in base_taxes._fields:
            candidates |= base_taxes.filtered(lambda t: t.l10n_co_edi_type.retention)
        if 'tributes' in base_taxes._fields:
            candidates |= base_taxes.filtered(lambda t: t.tributes in ('05', '06', '07'))
        candidates |= base_taxes.filtered(lambda t: t.amount_type == 'percent' and t.amount < 0)

        if already_applied_taxes:
            candidates -= already_applied_taxes
        return candidates
