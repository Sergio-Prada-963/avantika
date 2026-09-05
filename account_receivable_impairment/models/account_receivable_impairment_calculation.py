# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountReceivableImpairmentCalculation(models.Model):
    _name = 'account.receivable.impairment.calculation'
    _description = 'Cálculo de Deterioro de Cartera'
    _order = 'date desc, id desc'

    name = fields.Char(string='Referencia', required=True, copy=False,
                        default=lambda self: _('Nuevo'))
    date = fields.Date(string='Fecha de corte', required=True,
                        default=fields.Date.context_today)
    company_id = fields.Many2one(
        'res.company', string='Compañía', required=True,
        default=lambda self: self.env.company)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('calculated', 'Calculado'),
        ('posted', 'Contabilizado'),
        ('cancelled', 'Cancelado'),
    ], string='Estado', default='draft', copy=False)
    move_id = fields.Many2one('account.move', string='Asiento contable',
                               readonly=True, copy=False)
    line_ids = fields.One2many(
        'account.receivable.impairment.calculation.line', 'calculation_id',
        string='Detalle por factura', readonly=True)
    total_required = fields.Monetary(string='Total requerido', compute='_compute_totals')
    total_existing = fields.Monetary(string='Total ya registrado', compute='_compute_totals')
    total_adjustment = fields.Monetary(string='Ajuste neto', compute='_compute_totals')
    currency_id = fields.Many2one(related='company_id.currency_id')
    invoice_ids = fields.Many2many(
        'account.move', compute='_compute_invoice_ids', string='Facturas')
    invoice_count = fields.Integer(compute='_compute_invoice_ids')

    _sql_constraints = [
        ('date_company_uniq', 'unique(date, company_id)',
         'Ya existe un cálculo de deterioro para esta compañía en esta fecha de corte.'),
    ]

    @api.depends('line_ids.required_amount')
    def _compute_totals(self):
        for calc in self:
            calc.total_required = sum(calc.line_ids.mapped('required_amount'))
            existing_by_partner = calc._get_existing_provision_by_partner()
            calc.total_existing = sum(existing_by_partner.values())
            calc.total_adjustment = calc.total_required - calc.total_existing

    @api.depends('line_ids.move_id')
    def _compute_invoice_ids(self):
        for calc in self:
            calc.invoice_ids = calc.line_ids.move_id
            calc.invoice_count = len(calc.invoice_ids)

    def action_view_invoices(self):
        self.ensure_one()
        action = {
            'name': _('Facturas del Cálculo de Deterioro'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
        }
        if len(self.invoice_ids) == 1:
            action.update({'view_mode': 'form', 'res_id': self.invoice_ids.id})
        else:
            action.update({'view_mode': 'list,form', 'domain': [('id', 'in', self.invoice_ids.ids)]})
        return action

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'account.receivable.impairment.calculation') or _('Nuevo')
        calculations = super().create(vals_list)
        for calculation in calculations:
            try:
                calculation.action_calculate()
            except UserError:
                # Missing configuration (accounts, ranges): leave it in draft
                # so the user can complete the setup and calculate manually.
                pass
        return calculations

    def _get_open_receivable_lines(self):
        self.ensure_one()
        accounts = self.company_id._get_impairment_receivable_accounts()
        if not accounts:
            raise UserError(_(
                'La compañía no tiene cuentas por cobrar configuradas para evaluar.'))
        return self.env['account.move.line'].search([
            ('account_id', 'in', accounts.ids),
            ('move_id.move_type', 'in', ('out_invoice', 'out_refund')),
            ('move_id.payment_state', 'in', ('not_paid', 'partial')),
            ('parent_state', '=', 'posted'),
            ('reconciled', '=', False),
            ('company_id', '=', self.company_id.id),
            ('date', '<=', self.date),
            '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0),
        ])

    def _get_existing_provision_by_partner(self):
        """Saldo de la cuenta de provisión por tercero, leído del mayor (no de estado propio)."""
        self.ensure_one()
        if not self.company_id.impairment_provision_account_id:
            return {}
        groups = self.env['account.move.line']._read_group(
            domain=[
                ('account_id', '=', self.company_id.impairment_provision_account_id.id),
                ('parent_state', '=', 'posted'),
                ('company_id', '=', self.company_id.id),
                ('date', '<=', self.date),
            ],
            groupby=['partner_id'],
            aggregates=['balance:sum'],
        )
        # La cuenta de provisión es de naturaleza crédito: saldo existente = -(debe - haber)
        return {partner.id if partner else False: -balance for partner, balance in groups}

    def action_calculate(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Solo se puede calcular un registro en borrador.'))
        if not self.company_id.impairment_line_ids:
            raise UserError(_(
                'La compañía "%s" no tiene rangos de mora configurados (Contabilidad → '
                'Ajustes → Deterioro de Cartera).', self.company_id.name))
        self.line_ids.unlink()
        move_lines = self._get_open_receivable_lines()
        calc_line_vals = []
        # Group by invoice: a single invoice can have more than one open
        # receivable line (e.g. multi-installment payment terms), and it must
        # only appear once in the detail, not once per line.
        for move, lines in move_lines.grouped('move_id').items():
            due_date = min(
                l.date_maturity or l.move_id.invoice_date_due or l.date for l in lines
            )
            days_overdue = (self.date - due_date).days
            if days_overdue <= 0:
                continue
            bucket = self.company_id._get_impairment_bucket(days_overdue)
            if not bucket:
                continue
            percentage = bucket.percentage
            residual_amount = sum(lines.mapped('amount_residual'))
            calc_line_vals.append({
                'calculation_id': self.id,
                'move_line_id': lines[0].id,
                'partner_id': move.partner_id.id,
                'date_maturity': due_date,
                'days_overdue': days_overdue,
                'matrix_line_id': bucket.id,
                'residual_amount': residual_amount,
                'percentage': percentage,
                'required_amount': residual_amount * percentage / 100.0,
            })
        self.env['account.receivable.impairment.calculation.line'].create(calc_line_vals)
        self.state = 'calculated'

    def _prepare_move_lines(self):
        self.ensure_one()
        existing_by_partner = self._get_existing_provision_by_partner()
        required_by_partner = {}
        for line in self.line_ids:
            partner_id = line.partner_id.id
            required_by_partner[partner_id] = required_by_partner.get(
                partner_id, 0.0) + line.required_amount

        move_lines = []
        for partner_id, required in required_by_partner.items():
            existing = existing_by_partner.get(partner_id, 0.0)
            adjustment = required - existing
            if self.currency_id.is_zero(adjustment):
                continue
            partner_command = partner_id or False
            name = _('Ajuste deterioro de cartera %s', self.name)
            if adjustment > 0:
                move_lines.append((0, 0, {
                    'name': name,
                    'account_id': self.company_id.impairment_expense_account_id.id,
                    'partner_id': partner_command,
                    'debit': adjustment,
                    'credit': 0.0,
                }))
                move_lines.append((0, 0, {
                    'name': name,
                    'account_id': self.company_id.impairment_provision_account_id.id,
                    'partner_id': partner_command,
                    'debit': 0.0,
                    'credit': adjustment,
                }))
            else:
                move_lines.append((0, 0, {
                    'name': name,
                    'account_id': self.company_id.impairment_provision_account_id.id,
                    'partner_id': partner_command,
                    'debit': -adjustment,
                    'credit': 0.0,
                }))
                move_lines.append((0, 0, {
                    'name': name,
                    'account_id': self.company_id.impairment_expense_account_id.id,
                    'partner_id': partner_command,
                    'debit': 0.0,
                    'credit': -adjustment,
                }))
        return move_lines

    def action_post(self):
        self.ensure_one()
        if self.state != 'calculated':
            raise UserError(_('Solo se puede contabilizar un registro calculado.'))
        move_lines = self._prepare_move_lines()
        if not move_lines:
            raise UserError(_(
                'No hay ajuste que contabilizar: la provisión requerida coincide '
                'con la ya registrada para todos los terceros.'))
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.company_id.impairment_journal_id.id,
            'date': self.date,
            'ref': self.name,
            'line_ids': move_lines,
        })
        move.action_post()
        self.write({'move_id': move.id, 'state': 'posted'})

    def action_reset_to_draft(self):
        for calc in self:
            if calc.move_id and calc.move_id.state == 'posted':
                raise UserError(_(
                    'No se puede restablecer a borrador: el asiento "%s" ya está '
                    'contabilizado. Anúlelo primero.', calc.move_id.name))
            if calc.move_id:
                calc.move_id.unlink()
            calc.line_ids.unlink()
            calc.write({'move_id': False, 'state': 'draft'})

    def action_cancel(self):
        for calc in self:
            if calc.move_id and calc.move_id.state == 'posted':
                raise UserError(_(
                    'No se puede cancelar: el asiento "%s" ya está contabilizado. '
                    'Anúlelo primero.', calc.move_id.name))
            calc.write({'state': 'cancelled'})

    def action_view_move(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class AccountReceivableImpairmentCalculationLine(models.Model):
    _name = 'account.receivable.impairment.calculation.line'
    _description = 'Línea de Cálculo de Deterioro de Cartera'

    calculation_id = fields.Many2one(
        'account.receivable.impairment.calculation', string='Cálculo',
        required=True, ondelete='cascade')
    move_line_id = fields.Many2one('account.move.line', string='Apunte contable',
                                    required=True)
    move_id = fields.Many2one(related='move_line_id.move_id', string='Factura', store=True)
    partner_id = fields.Many2one('res.partner', string='Tercero')
    date_maturity = fields.Date(string='Fecha de vencimiento')
    days_overdue = fields.Integer(string='Días de mora')
    matrix_line_id = fields.Many2one(
        'account.receivable.impairment.matrix.line', string='Rango aplicado')
    residual_amount = fields.Monetary(string='Saldo pendiente')
    percentage = fields.Float(string='% Pérdida esperada', digits=0)
    required_amount = fields.Monetary(string='Provisión requerida')
    currency_id = fields.Many2one(related='calculation_id.currency_id')
