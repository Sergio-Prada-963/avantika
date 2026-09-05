# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountPaymentSchedule(models.Model):
    _name = 'account.payment.schedule'
    _description = "Programación de Pago a Proveedores"
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(default=lambda self: _("Nuevo"), copy=False, readonly=True)
    date = fields.Date(
        string="Fecha de Pago", default=fields.Date.context_today,
        required=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', string="Compañía", required=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    journal_id = fields.Many2one(
        'account.journal', string="Diario de Pago", required=True,
        domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]",
        default=lambda self: self.env.company.aps_payment_journal_id)
    state = fields.Selection([
        ('draft', "Borrador"),
        ('confirmed', "Confirmado"),
        ('cancelled', "Cancelado"),
    ], default='draft', required=True, tracking=True, copy=False)
    auto_generated = fields.Boolean(
        string="Generado Automáticamente", readonly=True, copy=False)
    note = fields.Text(string="Notas")

    line_ids = fields.One2many(
        'account.payment.schedule.line', 'schedule_id', string="Facturas",
        copy=False)
    payment_ids = fields.One2many(
        'account.payment', 'payment_schedule_id', string="Pagos Generados",
        readonly=True, copy=False)
    payment_count = fields.Integer(compute='_compute_payment_count')
    invoice_count = fields.Integer(compute='_compute_invoice_count')

    total_residual = fields.Monetary(compute='_compute_amounts', store=True)
    total_to_pay = fields.Monetary(compute='_compute_amounts', store=True)
    total_advance = fields.Monetary(compute='_compute_amounts', store=True)

    @api.depends('line_ids.amount_residual', 'line_ids.amount_to_pay', 'line_ids.amount_advance')
    def _compute_amounts(self):
        for schedule in self:
            schedule.total_residual = sum(schedule.line_ids.mapped('amount_residual'))
            schedule.total_to_pay = sum(schedule.line_ids.mapped('amount_to_pay'))
            schedule.total_advance = sum(schedule.line_ids.mapped('amount_advance'))

    def _compute_payment_count(self):
        for schedule in self:
            schedule.payment_count = len(schedule.payment_ids)

    @api.depends('line_ids.move_id')
    def _compute_invoice_count(self):
        for schedule in self:
            schedule.invoice_count = len(schedule.line_ids.move_id)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _("Nuevo")) == _("Nuevo"):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'account.payment.schedule') or _("Nuevo")
        return super().create(vals_list)

    def action_add_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Agregar Facturas"),
            'res_model': 'account.payment.schedule.add.lines',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_schedule_id': self.id},
        }

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Facturas Relacionadas"),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.line_ids.move_id.ids)],
            'context': {'create': False},
        }

    def action_view_payments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Pagos Generados"),
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.payment_ids.ids)],
        }

    def action_draft(self):
        for schedule in self:
            if schedule.state != 'cancelled':
                raise UserError(_("Solo se puede reabrir una programación cancelada."))
            schedule.state = 'draft'

    def action_cancel(self):
        for schedule in self:
            if schedule.state == 'confirmed':
                raise UserError(_(
                    "No se puede cancelar una programación ya confirmada; "
                    "los pagos generados deben anularse individualmente."
                ))
            schedule.state = 'cancelled'

    def action_confirm(self):
        for schedule in self:
            schedule._check_before_confirm()
            schedule._generate_payments()
            schedule.state = 'confirmed'
        return True

    def _check_before_confirm(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Solo se puede confirmar una programación en borrador."))
        if not self.line_ids:
            raise UserError(_("Agregue al menos una factura antes de confirmar."))
        if not self.journal_id:
            raise UserError(_("Configure el diario de pago antes de confirmar."))
        if not self.journal_id._get_available_payment_method_lines('outbound'):
            raise UserError(_(
                "El diario '%s' no tiene ningún método de pago habilitado "
                "para pagos salientes (proveedor). Vaya a Contabilidad > "
                "Configuración > Diarios, abra ese diario y agregue un "
                "método en la pestaña 'Pagos Salientes'."
            ) % self.journal_id.display_name)

    def _generate_payments(self):
        self.ensure_one()
        partners = self.line_ids.partner_id
        for partner in partners:
            lines = self.line_ids.filtered(lambda l: l.partner_id == partner)
            self._generate_payment_for_partner(partner, lines)

    def _generate_payment_for_partner(self, partner, lines):
        self.ensure_one()
        lines = lines.sorted('id')
        main_line, extra_lines = lines[0], lines[1:]

        pay_amounts = {
            line: min(line.amount_to_pay, line.amount_residual) for line in lines
        }
        total_advance = sum(lines.mapped('amount_advance'))
        total_amount = sum(pay_amounts.values()) + total_advance

        write_off_line_vals = []
        for line in extra_lines:
            write_off_line_vals.append({
                'name': line._get_move_line_name(),
                'account_id': line._get_payable_account().id,
                'partner_id': partner.id,
                'amount_currency': pay_amounts[line],
                'balance': pay_amounts[line],
            })

        advance_account = self.env['account.account']
        if total_advance:
            advance_account = (
                partner.apm_advance_payable_account_id
                or self.company_id.apm_advance_payable_account_id
            )
            if not advance_account:
                raise UserError(_(
                    "El monto a pagar de %(partner)s supera lo adeudado y "
                    "generaría un anticipo, pero no hay una cuenta de "
                    "anticipos a proveedor configurada ni en el contacto ni "
                    "en Ajustes de Contabilidad.",
                    partner=partner.display_name,
                ))
            write_off_line_vals.append({
                'name': _("Anticipo a proveedor - %s") % self.name,
                'account_id': advance_account.id,
                'partner_id': partner.id,
                'amount_currency': total_advance,
                'balance': total_advance,
            })

        # `force_payment_move` obliga a Odoo a resolver una cuenta de
        # "outstanding payments" por defecto (plan de cuentas o cuenta de
        # transferencias de la compañía) para poder generar el asiento del
        # pago de inmediato, sin depender de que el método de pago del
        # diario tenga configurada manualmente su propia cuenta puente.
        payment = self.env['account.payment'].with_context(force_payment_move=True).create({
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': partner.id,
            'amount': total_amount,
            'date': self.date,
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'destination_account_id': main_line._get_payable_account().id,
            'memo': _("Programación de pago %s") % self.name,
            'payment_schedule_id': self.id,
            'write_off_line_vals': write_off_line_vals,
        })
        payment.action_post()
        self._reconcile_payment_lines(payment, main_line, extra_lines, advance_account)
        return payment

    def _reconcile_payment_lines(self, payment, main_line, extra_lines, advance_account):
        self.ensure_one()
        # Las líneas del pago se crean en un orden conocido: primero la
        # línea de liquidez (banco/caja, otra cuenta, ya excluida por el
        # filtro), luego la contrapartida principal (`main_line`) y después
        # una línea de "write-off" por cada factura extra, en el mismo
        # orden en que se armó `write_off_line_vals`. Se emparejan por
        # posición (orden de creación = orden de id) en vez de por nombre,
        # que es más frágil. Se excluye explícitamente la cuenta de
        # anticipos: aunque no debería ser de tipo "por pagar", el campo de
        # configuración no lo restringe, así que si coincidiera se
        # confundiría con una línea de factura.
        payable_move_lines = payment.move_id.line_ids.filtered(
            lambda l: l.account_id.account_type == 'liability_payable'
            and l.account_id != advance_account
            and not l.reconciled
        ).sorted('id')
        schedule_lines = [main_line] + list(extra_lines)

        if len(payable_move_lines) != len(schedule_lines):
            found = "; ".join(
                "%s: %s (%.2f)" % (l.account_id.code, l.name or '', l.balance)
                for l in payment.move_id.line_ids
            ) or "(sin líneas)"
            expected = "; ".join(
                "%s (factura %s)" % (l._get_move_line_name(), l.move_id.name)
                for l in schedule_lines
            )
            raise UserError(_(
                "No se pudo determinar con certeza qué línea del pago "
                "generado corresponde a cada factura de %(partner)s. "
                "Revise y concilie manualmente el pago %(payment)s.\n\n"
                "Líneas encontradas en el asiento: %(found)s\n"
                "Facturas esperadas: %(expected)s"
            ) % {
                'partner': payment.partner_id.display_name,
                'payment': payment.name or payment.display_name,
                'found': found,
                'expected': expected,
            })

        for payment_line, schedule_line in zip(payable_move_lines, schedule_lines):
            self._reconcile_pair(payment_line, schedule_line)

    def _reconcile_pair(self, payment_line, schedule_line):
        if not payment_line:
            return
        invoice_line = schedule_line.move_id.line_ids.filtered(
            lambda l: l.account_id.account_type == 'liability_payable' and not l.reconciled
        )
        if invoice_line:
            (payment_line + invoice_line).reconcile()

    @api.model
    def _cron_generate_payment_schedules(self):
        for company in self.env['res.company'].search([]):
            self.with_company(company)._generate_scheduled_payment_for_company(company)

    @api.model
    def _generate_scheduled_payment_for_company(self, company):
        if not company.aps_payment_journal_id:
            # La compañía no configuró el diario de pago por defecto en
            # Ajustes: no se puede generar la programación automáticamente.
            return self.env['account.payment.schedule']

        days_ahead = company.aps_due_days_ahead or 0
        limit_date = fields.Date.context_today(self) + timedelta(days=days_ahead)
        domain = [
            ('company_id', '=', company.id),
            ('move_type', 'in', ('in_invoice', 'in_refund')),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('invoice_date_due', '!=', False),
            ('invoice_date_due', '<=', limit_date),
            ('currency_id', '=', company.currency_id.id),
        ]
        moves = self.env['account.move'].search(domain)

        already_scheduled = self.env['account.payment.schedule.line'].search([
            ('move_id', 'in', moves.ids),
            ('schedule_id.state', 'in', ('draft', 'confirmed')),
        ]).move_id
        moves -= already_scheduled
        if not moves:
            return self.env['account.payment.schedule']

        schedule = self.create({
            'company_id': company.id,
            'date': fields.Date.context_today(self),
            'journal_id': company.aps_payment_journal_id.id,
            'auto_generated': True,
        })
        self.env['account.payment.schedule.line'].create([{
            'schedule_id': schedule.id,
            'move_id': move.id,
            'amount_to_pay': move.amount_residual,
        } for move in moves])
        return schedule
