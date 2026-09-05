# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountPaymentDynamicLine(models.Model):
    """Línea de asiento adicional (contrapartida por factura o retención por
    impuesto agregado) para un pago creado desde el registro de pago
    multifactura. Vive aparte del pago para poder calcularse en el wizard
    (transient) y sobrevivir a la creación real del account.payment."""
    _name = 'account.payment.dynamic.line'
    _description = 'Línea dinámica de contrapartida/retención de un pago multifactura'

    payment_id = fields.Many2one('account.payment', required=True, ondelete='cascade')
    kind = fields.Selection(
        [('counterpart', 'Contrapartida'), ('withholding', 'Retención')],
        required=True,
    )
    move_id = fields.Many2one('account.move', string='Factura de Origen')
    tax_id = fields.Many2one('account.tax')
    account_id = fields.Many2one('account.account', required=True)
    partner_id = fields.Many2one('res.partner')
    currency_id = fields.Many2one('res.currency', required=True)
    amount_currency = fields.Monetary(currency_field='currency_id')
    balance = fields.Monetary(currency_field='company_currency_id')
    company_currency_id = fields.Many2one(related='payment_id.company_id.currency_id')
    name = fields.Char()

    def _to_move_line_vals(self, default_name):
        self.ensure_one()
        return {
            'name': self.name or default_name,
            'date_maturity': self.payment_id.date,
            'partner_id': self.partner_id.id,
            'account_id': self.account_id.id,
            'currency_id': self.currency_id.id,
            'balance': self.balance,
            'amount_currency': self.amount_currency,
        }
