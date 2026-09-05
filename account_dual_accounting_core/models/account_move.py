# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    accounting_book_id = fields.Many2one(
        'account.book', string="Libro Contable",
        default=lambda self: self._get_default_accounting_book(),
        index=True, copy=False,
        help="Libro contable (método) al que pertenece este asiento. Los "
             "asientos del libro primario generan automáticamente su "
             "espejo en el libro secundario al contabilizarse.",
    )
    is_dual_generated = fields.Boolean(
        string="Generado Automáticamente por Réplica Dual",
        default=False, copy=False, readonly=True,
    )
    origin_move_id = fields.Many2one(
        'account.move', string="Asiento Origen",
        readonly=True, copy=False, index=True,
        help="Asiento del libro primario que generó este asiento espejo.",
    )
    mirror_move_id = fields.Many2one(
        'account.move', string="Asiento Espejo",
        readonly=True, copy=False,
        help="Asiento generado en el libro secundario a partir de este asiento.",
    )
    mirror_move_count = fields.Integer(compute='_compute_mirror_move_count')

    @api.model
    def _get_default_accounting_book(self):
        return self.env['account.book']._get_default_primary_book()

    def _compute_mirror_move_count(self):
        for move in self:
            move.mirror_move_count = 1 if move.mirror_move_id else 0

    def action_view_mirror_move(self):
        self.ensure_one()
        if not self.mirror_move_id:
            return
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.mirror_move_id.id,
        }

    def action_post(self):
        res = super().action_post()
        for move in self:
            if move.is_dual_generated or not move.accounting_book_id or move.mirror_move_id:
                continue
            if move.accounting_book_id.type != 'primary':
                continue
            secondary_book = self.env['account.book']._get_default_secondary_book(move.company_id)
            if secondary_book:
                move._generate_secondary_book_entry(secondary_book)
        return res

    def _generate_secondary_book_entry(self, secondary_book):
        self.ensure_one()
        secondary_journal = secondary_book._get_mirror_journal(self.journal_id)
        if not secondary_journal:
            raise UserError(_(
                "No se encontró un diario del tipo '%(journal_type)s' vinculado "
                "al libro contable secundario '%(book)s'. Configure un diario "
                "espejo antes de contabilizar.",
                journal_type=self.journal_id.type, book=secondary_book.name,
            ))

        line_vals = []
        for line in self.line_ids:
            if not line.account_id:
                continue
            secondary_account = line.account_id.secondary_account_id or line.account_id
            line_vals.append((0, 0, {
                'name': line.name,
                'account_id': secondary_account.id,
                'partner_id': line.partner_id.id,
                'debit': line.debit,
                'credit': line.credit,
                'currency_id': line.currency_id.id,
                'amount_currency': line.amount_currency,
            }))

        secondary_move = self.env['account.move'].create({
            'move_type': 'entry',
            'ref': _("Réplica %(book)s de %(origin)s", book=secondary_book.code, origin=self.name or self.ref),
            'date': self.date,
            'journal_id': secondary_journal.id,
            'company_id': self.company_id.id,
            'partner_id': self.partner_id.id,
            'currency_id': self.currency_id.id,
            'accounting_book_id': secondary_book.id,
            'is_dual_generated': True,
            'origin_move_id': self.id,
            'line_ids': line_vals,
        })
        secondary_move.action_post()
        self.mirror_move_id = secondary_move

    def button_draft(self):
        for move in self:
            if move.is_dual_generated:
                raise UserError(_(
                    "El asiento '%(move)s' fue generado automáticamente por "
                    "la réplica dual. Para modificarlo, primero reabra y "
                    "corrija el asiento origen en el libro primario.",
                    move=move.name or move.ref,
                ))
        return super().button_draft()
