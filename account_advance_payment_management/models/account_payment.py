from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    apm_is_advance = fields.Boolean(
        string="¿Es Anticipo?",
        help="Marca este cobro/pago como un anticipo sin factura previa. El "
             "importe se contabilizará en la cuenta de anticipos configurada "
             "en lugar de la cuenta por cobrar/pagar del tercero.",
    )
    apm_advance_account_id = fields.Many2one(
        'account.account',
        string="Cuenta de Anticipo",
        domain="[('company_ids', 'in', company_id), ('reconcile', '=', True), "
               "('account_type', 'in', ('asset_prepayments', 'asset_current', 'liability_current'))]",
        help="Cuenta de pasivo (cliente) o de activo (proveedor) donde se "
             "registrará este anticipo.",
    )
    apm_residual = fields.Monetary(
        string="Anticipo Disponible",
        compute='_compute_apm_residual',
        store=True,
        help="Parte de este anticipo que aún no se ha legalizado/aplicado "
             "contra ninguna factura.",
    )

    @api.depends('apm_advance_account_id', 'apm_is_advance')
    def _compute_destination_account_id(self):
        super()._compute_destination_account_id()
        for payment in self:
            if payment.apm_is_advance and payment.apm_advance_account_id:
                payment.destination_account_id = payment.apm_advance_account_id.id

    @api.onchange('journal_id', 'payment_type', 'apm_is_advance', 'partner_id')
    def _onchange_apm_advance_account(self):
        if not self.apm_is_advance:
            return
        company = self.journal_id.company_id or self.company_id
        if self.payment_type == 'inbound':
            self.apm_advance_account_id = (
                self.partner_id.apm_advance_receivable_account_id
                or company.apm_advance_receivable_account_id
            )
            if company.apm_advance_journal_customer_id:
                self.journal_id = company.apm_advance_journal_customer_id
        elif self.payment_type == 'outbound':
            self.apm_advance_account_id = (
                self.partner_id.apm_advance_payable_account_id
                or company.apm_advance_payable_account_id
            )
            if company.apm_advance_journal_supplier_id:
                self.journal_id = company.apm_advance_journal_supplier_id

    def _prepare_move_counterpart_lines(self, default_values):
        vals_list = super()._prepare_move_counterpart_lines(default_values)
        if self.apm_is_advance and self.apm_advance_account_id and self.destination_account_id == self.apm_advance_account_id:
            for vals in vals_list:
                vals['apm_is_advance_line'] = True
        return vals_list

    @api.depends(
        'apm_is_advance',
        'move_id.line_ids.apm_is_advance_line',
        'move_id.line_ids.amount_residual',
        'move_id.line_ids.amount_residual_currency',
    )
    def _compute_apm_residual(self):
        for payment in self:
            if not payment.apm_is_advance:
                payment.apm_residual = 0.0
                continue
            residual = 0.0
            for line in payment.move_id.line_ids.filtered('apm_is_advance_line'):
                if line.currency_id:
                    residual += abs(line.amount_residual_currency)
                else:
                    residual += abs(line.amount_residual)
            payment.apm_residual = residual
