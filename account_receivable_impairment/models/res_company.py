# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

PERIODICITY_MONTHS = {
    'monthly': 1,
    'bimonthly': 2,
    'quarterly': 3,
    'semiannual': 6,
    'annual': 12,
}


class ResCompany(models.Model):
    _inherit = 'res.company'

    impairment_periodicity = fields.Selection([
        ('monthly', 'Mensual'),
        ('bimonthly', 'Bimensual'),
        ('quarterly', 'Trimestral'),
        ('semiannual', 'Semestral'),
        ('annual', 'Anual'),
    ], string='Periodicidad de Cálculo Automático', default='monthly', required=True,
        help='Cada cuánto se debe generar automáticamente (en borrador) un '
             'nuevo cálculo de deterioro de cartera para esta compañía.')
    impairment_expense_account_id = fields.Many2one(
        'account.account', string='Cuenta de gasto por deterioro',
        domain="[('company_ids', 'in', id)]",
        help='Cuenta a la que se debita el gasto por deterioro de cartera.')
    impairment_provision_account_id = fields.Many2one(
        'account.account', string='Cuenta de provisión por deterioro',
        domain="[('company_ids', 'in', id)]",
        help='Cuenta contra-activo donde se acumula la provisión de cartera.')
    impairment_journal_id = fields.Many2one(
        'account.journal', string='Diario de deterioro de cartera',
        domain="[('type', '=', 'general'), ('company_id', '=', id)]",
        help='Diario contable donde se registran los asientos de ajuste.')
    impairment_line_ids = fields.One2many(
        'account.receivable.impairment.matrix.line', 'company_id',
        string='Rangos de mora')

    @api.constrains('impairment_line_ids')
    def _check_impairment_line_ids(self):
        for company in self:
            lines = company.impairment_line_ids.sorted('day_from')
            open_ended = lines.filtered(lambda l: not l.day_to)
            if len(open_ended) > 1:
                raise ValidationError(_(
                    'Solo un rango puede quedar abierto (sin día final) en los rangos '
                    'de mora de "%s".', company.name))
            if open_ended and open_ended != lines[-1]:
                raise ValidationError(_(
                    'El rango abierto (sin día final) debe ser el de mayor "Día desde" '
                    'en los rangos de mora de "%s".', company.name))
            previous_to = None
            for line in lines:
                if line.day_to and line.day_from > line.day_to:
                    raise ValidationError(_(
                        '"Día desde" no puede ser mayor que "Día hasta" en los rangos '
                        'de mora de "%s".', company.name))
                if previous_to is not None and line.day_from <= previous_to:
                    raise ValidationError(_(
                        'Los rangos de mora de "%s" no pueden solaparse.', company.name))
                previous_to = line.day_to

    def _get_impairment_bucket(self, days_overdue):
        """Devuelve el rango de mora cuyo intervalo contiene ``days_overdue``."""
        self.ensure_one()
        for line in self.impairment_line_ids.sorted('day_from'):
            if days_overdue < line.day_from:
                continue
            if not line.day_to or days_overdue <= line.day_to:
                return line
        return self.env['account.receivable.impairment.matrix.line']

    def _get_impairment_receivable_accounts(self):
        self.ensure_one()
        marked_accounts = self.env['account.account'].search([
            ('account_type', '=', 'asset_receivable'),
            ('company_ids', 'in', self.id),
            ('impairment_evaluate', '=', True),
        ])
        if marked_accounts:
            return marked_accounts
        return self.env['account.account'].search([
            ('account_type', '=', 'asset_receivable'),
            ('company_ids', 'in', self.id),
        ])

    @api.model
    def _cron_generate_periodic_impairment_calculations(self):
        """Crea, en borrador, un nuevo cálculo de deterioro por cada compañía
        que tenga el deterioro configurado y cuya periodicidad ya se cumplió
        desde su último cálculo."""
        Calculation = self.env['account.receivable.impairment.calculation']
        today = fields.Date.context_today(self)
        for company in self.search([]):
            if not (
                company.impairment_journal_id
                and company.impairment_expense_account_id
                and company.impairment_provision_account_id
            ):
                continue
            months = PERIODICITY_MONTHS.get(company.impairment_periodicity)
            if not months:
                continue

            last_calculation = Calculation.search([
                ('company_id', '=', company.id),
            ], order='date desc', limit=1)
            if last_calculation and today < last_calculation.date + relativedelta(months=months):
                continue

            already_today = Calculation.search_count([
                ('company_id', '=', company.id),
                ('date', '=', today),
            ])
            if already_today:
                continue

            Calculation.create({
                'date': today,
                'company_id': company.id,
            })
