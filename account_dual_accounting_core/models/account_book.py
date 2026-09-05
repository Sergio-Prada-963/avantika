# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccountBook(models.Model):
    _name = 'account.book'
    _description = 'Libro Contable / Método (NIIF, Fiscal, ...)'
    _order = 'type, sequence, id'

    name = fields.Char(string="Nombre del Método", required=True)
    code = fields.Char(string="Código Corto", required=True)
    sequence = fields.Integer(default=10)
    type = fields.Selection([
        ('primary', 'Método Primario / Operativo'),
        ('secondary', 'Método Secundario / Ajuste'),
    ], string="Tipo de Libro", default='primary', required=True)
    company_id = fields.Many2one(
        'res.company', string="Compañía",
        default=lambda self: self.env.company,
    )
    journal_ids = fields.Many2many(
        'account.journal', string="Diarios Vinculados",
        help="Diarios que pertenecen a este libro contable. El motor de "
             "réplica dual busca aquí el diario espejo según el tipo de "
             "diario del asiento origen.",
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_company_uniq', 'unique(code, company_id)',
         'El código del libro contable debe ser único por compañía.'),
    ]

    @api.constrains('company_id', 'journal_ids')
    def _check_journal_company(self):
        for book in self:
            mismatched = book.journal_ids.filtered(
                lambda j: book.company_id and j.company_id != book.company_id
            )
            if mismatched:
                raise ValidationError(
                    "Todos los diarios vinculados a un libro contable deben "
                    "pertenecer a la misma compañía que el libro."
                )

    def _get_mirror_journal(self, journal):
        """Diario del mismo tipo que 'journal', perteneciente a este libro."""
        self.ensure_one()
        return self.journal_ids.filtered(lambda j: j.type == journal.type)[:1]

    @api.model
    def _get_default_primary_book(self, company=None):
        company = company or self.env.company
        return self.search([
            ('type', '=', 'primary'),
            ('company_id', '=', company.id),
        ], limit=1)

    @api.model
    def _get_default_secondary_book(self, company=None):
        company = company or self.env.company
        return self.search([
            ('type', '=', 'secondary'),
            ('company_id', '=', company.id),
        ], limit=1)
