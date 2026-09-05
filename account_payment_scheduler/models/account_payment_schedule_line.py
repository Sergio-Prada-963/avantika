# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountPaymentScheduleLine(models.Model):
    _name = 'account.payment.schedule.line'
    _description = "Línea de Programación de Pago"

    schedule_id = fields.Many2one(
        'account.payment.schedule', string="Programación", required=True,
        ondelete='cascade', index=True)
    company_id = fields.Many2one(related='schedule_id.company_id', store=True)
    state = fields.Selection(related='schedule_id.state', store=True)

    move_id = fields.Many2one(
        'account.move', string="Factura", required=True,
        domain="[('move_type', 'in', ('in_invoice', 'in_refund')), "
               "('state', '=', 'posted'), "
               "('payment_state', 'in', ('not_paid', 'partial'))]")
    partner_id = fields.Many2one(related='move_id.partner_id', store=True, string="Proveedor")
    invoice_date = fields.Date(related='move_id.invoice_date', string="Fecha Factura")
    invoice_date_due = fields.Date(related='move_id.invoice_date_due', string="Vencimiento")
    ref = fields.Char(related='move_id.ref', string="Referencia")
    currency_id = fields.Many2one(related='move_id.currency_id', string="Moneda")
    amount_total = fields.Monetary(related='move_id.amount_total', string="Total Factura")
    amount_residual = fields.Monetary(related='move_id.amount_residual', string="Saldo Pendiente", store=True)

    amount_to_pay = fields.Monetary(string="Monto a Pagar", currency_field='currency_id')
    amount_advance = fields.Monetary(
        string="Excedente (Anticipo)", compute='_compute_amount_advance', store=True,
        currency_field='currency_id',
        help="Parte del monto a pagar que excede el saldo pendiente de esta "
             "factura y que se registrará como anticipo a proveedor.")

    _sql_constraints = [
        ('schedule_move_uniq', 'unique(schedule_id, move_id)',
         "Esta factura ya está incluida en esta programación de pago."),
    ]

    @api.depends('amount_to_pay', 'amount_residual')
    def _compute_amount_advance(self):
        for line in self:
            line.amount_advance = max(line.amount_to_pay - line.amount_residual, 0.0)

    @api.onchange('move_id')
    def _onchange_move_id(self):
        for line in self:
            if line.move_id:
                line.amount_to_pay = line.move_id.amount_residual

    @api.constrains('amount_to_pay')
    def _check_amount_to_pay(self):
        for line in self:
            if line.amount_to_pay <= 0:
                raise ValidationError(_(
                    "El monto a pagar de la factura %s debe ser mayor a cero."
                ) % line.move_id.display_name)

    @api.constrains('move_id')
    def _check_move_currency(self):
        for line in self:
            if line.move_id and line.move_id.currency_id != line.move_id.company_id.currency_id:
                raise ValidationError(_(
                    "La factura %s está en una moneda distinta a la de la "
                    "compañía. Esta funcionalidad por ahora solo soporta "
                    "facturas en la moneda de la compañía."
                ) % line.move_id.display_name)

    def _get_payable_account(self):
        self.ensure_one()
        account = self.move_id.line_ids.filtered(
            lambda l: l.account_id.account_type == 'liability_payable'
        )[:1].account_id
        if not account:
            raise UserError(_(
                "No se encontró la cuenta por pagar de la factura %s."
            ) % self.move_id.display_name)
        return account

    def _get_move_line_name(self):
        self.ensure_one()
        return _("Pago %s") % self.move_id.name
