# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    account_book_ids = fields.Many2many(
        'account.book', string="Libros Contables",
        compute='_compute_account_book_ids', store=False,
    )

    def _compute_account_book_ids(self):
        books = self.env['account.book'].search([('journal_ids', 'in', self.ids)])
        for journal in self:
            journal.account_book_ids = books.filtered(lambda b: journal in b.journal_ids)
