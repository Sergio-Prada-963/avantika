from odoo import _, api, fields, models
from odoo.exceptions import UserError

INVOICE_SIDE_MOVE_TYPES = ('out_invoice', 'in_refund')


class AccountMove(models.Model):
    _inherit = 'account.move'

    apm_is_legalization_entry = fields.Boolean(
        string="Es Asiento de Legalización de Anticipo",
        help="Marca técnica para identificar los asientos de reclasificación "
             "generados automáticamente al legalizar un anticipo contra una "
             "factura.",
    )
    apm_advance_payment_ids = fields.Many2many(
        'account.payment', compute='_compute_apm_advance_payment_ids',
        string="Pagos de Anticipo Aplicados",
    )
    apm_advance_payment_count = fields.Integer(compute='_compute_apm_advance_payment_ids')

    def _compute_apm_advance_payment_ids(self):
        for move in self:
            receivable_lines = move.line_ids.filtered(
                lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
            )
            partials = receivable_lines.matched_debit_ids | receivable_lines.matched_credit_ids
            counterpart_lines = (partials.debit_move_id | partials.credit_move_id) - receivable_lines
            legalization_moves = counterpart_lines.move_id.filtered('apm_is_legalization_entry')

            advance_side_lines = legalization_moves.line_ids.filtered(lambda l: l.account_id.apm_advance_account)
            advance_partials = advance_side_lines.matched_debit_ids | advance_side_lines.matched_credit_ids
            origin_advance_lines = (advance_partials.debit_move_id | advance_partials.credit_move_id) - advance_side_lines

            payments = origin_advance_lines.payment_id
            move.apm_advance_payment_ids = payments
            move.apm_advance_payment_count = len(payments)

    def action_view_apm_advance_payments(self):
        self.ensure_one()
        payments = self.apm_advance_payment_ids
        action = {
            'name': _("Pago de Anticipo Aplicado"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }
        if len(payments) == 1:
            action.update({'view_mode': 'form', 'res_id': payments.id})
        else:
            action.update({'view_mode': 'list,form', 'domain': [('id', 'in', payments.ids)]})
        return action

    def _compute_payments_widget_to_reconcile_info(self):
        super()._compute_payments_widget_to_reconcile_info()

        advance_accounts = self.env['account.account'].search([('apm_advance_account', '=', True)])
        if not advance_accounts:
            return

        for move in self:
            if move.state != 'posted' or move.payment_state not in ('not_paid', 'partial') \
                    or not move.is_invoice(include_receipts=True):
                continue

            domain = [
                ('account_id', 'in', advance_accounts.ids),
                ('parent_state', '=', 'posted'),
                *move._check_company_domain(move.company_id),
                ('partner_id', '=', move.commercial_partner_id.id),
                ('reconciled', '=', False),
                ('balance', '<' if move.is_inbound() else '>', 0.0),
                '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0),
            ]
            advance_lines = self.env['account.move.line'].search(domain)
            if not advance_lines:
                continue

            widget_vals = move.invoice_outstanding_credits_debits_widget or {
                'outstanding': True,
                'content': [],
                'move_id': move.id,
                'title': _('Outstanding credits') if move.is_inbound() else _('Outstanding debits'),
            }
            known_ids = {content['id'] for content in widget_vals['content']}

            for line in advance_lines:
                if line.id in known_ids:
                    continue
                if line.currency_id == move.currency_id:
                    amount = abs(line.amount_residual_currency)
                else:
                    amount = line.company_currency_id._convert(
                        abs(line.amount_residual), move.currency_id, move.company_id, line.date,
                    )
                if move.currency_id.is_zero(amount):
                    continue
                widget_vals['content'].append({
                    'journal_name': line.ref or line.move_id.name,
                    'amount': amount,
                    'currency_id': move.currency_id.id,
                    'id': line.id,
                    'move_id': line.move_id.id,
                    'date': fields.Date.to_string(line.date),
                    'account_payment_id': line.payment_id.id,
                    'move_ref': line.ref or "",
                })

            if widget_vals['content']:
                move.invoice_outstanding_credits_debits_widget = widget_vals

    def js_assign_outstanding_line(self, line_id):
        self.ensure_one()
        line = self.env['account.move.line'].browse(line_id)
        if line.account_id.apm_advance_account:
            return bool(self._apm_legalize_advance(line))
        return super().js_assign_outstanding_line(line_id)

    def js_remove_outstanding_partial(self, partial_id):
        self.ensure_one()
        partial = self.env['account.partial.reconcile'].browse(partial_id)
        legalization_move = (partial.debit_move_id.move_id | partial.credit_move_id.move_id) \
            .filtered('apm_is_legalization_entry')
        if legalization_move:
            legalization_move.line_ids.remove_move_reconcile()
            legalization_move.button_draft()
            legalization_move.button_cancel()
            return legalization_move.unlink()
        return super().js_remove_outstanding_partial(partial_id)

    def _apm_legalize_advance(self, advance_line):
        """Create and post the reclassification entry that moves an advance
        payment from its advance account to the partner's receivable/payable
        account, and reconcile it against both the advance payment and this
        invoice."""
        self.ensure_one()

        invoice_lines = self.line_ids.filtered(
            lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable') and not l.reconciled
        )
        if not invoice_lines:
            raise UserError(_("This document has no open receivable/payable line to legalize the advance against."))

        counterpart_account = invoice_lines[0].account_id
        invoice_lines = invoice_lines.filtered(lambda l: l.account_id == counterpart_account)

        is_customer_side = self.move_type in INVOICE_SIDE_MOVE_TYPES
        journal = (
            self.company_id.apm_advance_journal_customer_id if is_customer_side
            else self.company_id.apm_advance_journal_supplier_id
        )
        if not journal:
            raise UserError(_(
                "Please configure the Advance Journal (Customers/Vendors) in "
                "Accounting Settings before applying an advance payment."
            ))

        advance_amount = abs(advance_line.amount_residual)
        invoice_amount = sum(abs(l.amount_residual) for l in invoice_lines)
        amount = min(advance_amount, invoice_amount)
        if self.company_currency_id.is_zero(amount):
            return False

        partner = advance_line.partner_id

        legalization_move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': journal.id,
            'date': fields.Date.context_today(self),
            'partner_id': partner.id,
            'ref': _("Legalización de anticipo %(advance)s en %(invoice)s",
                     advance=advance_line.move_id.name, invoice=self.name),
            'apm_is_legalization_entry': True,
            'line_ids': [
                (0, 0, {
                    'name': _("Legalización de anticipo"),
                    'account_id': advance_line.account_id.id,
                    'partner_id': partner.id,
                    'debit': amount if is_customer_side else 0.0,
                    'credit': 0.0 if is_customer_side else amount,
                }),
                (0, 0, {
                    'name': _("Legalización de anticipo"),
                    'account_id': counterpart_account.id,
                    'partner_id': partner.id,
                    'debit': 0.0 if is_customer_side else amount,
                    'credit': amount if is_customer_side else 0.0,
                }),
            ],
        })
        legalization_move.action_post()

        advance_side = legalization_move.line_ids.filtered(lambda l: l.account_id == advance_line.account_id)
        invoice_side = legalization_move.line_ids.filtered(lambda l: l.account_id == counterpart_account)

        (advance_side + advance_line).reconcile()
        (invoice_side + invoice_lines).reconcile()
        return legalization_move


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    apm_is_advance_line = fields.Boolean(
        string="Es Línea de Anticipo",
        help="Marca técnica: esta línea contable pertenece a una cuenta de "
             "anticipo, ya sea del pago original o del asiento de "
             "legalización.",
    )
