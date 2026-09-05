# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountPaymentRegisterInvoiceLine(models.TransientModel):
    _name = 'account.payment.register.invoice.line'
    _description = 'Factura incluida en el registro de pago multifactura'
    _order = 'invoice_date_due, id'

    register_id = fields.Many2one(
        'account.payment.register', required=True, ondelete='cascade')
    # NOT readonly: the web client omits readonly fields from the vals it
    # sends on the wizard's first real save (everything before that runs in
    # a virtual onchange record), which made every row arrive at the server
    # without move_id and get silently dropped by create() below. It's not
    # user-editable anyway since the column is hidden (column_invisible="1"
    # in the view).
    move_id = fields.Many2one('account.move', required=True, ondelete='cascade')
    name = fields.Char(related='move_id.name', string='Número')
    partner_id = fields.Many2one(related='move_id.partner_id', string='Tercero', store=True)
    invoice_date_due = fields.Date(related='move_id.invoice_date_due', string='Fecha Vencimiento')
    currency_id = fields.Many2one(related='move_id.currency_id')
    amount_untaxed = fields.Monetary(
        related='move_id.amount_untaxed', string='Valor sin Impuesto', currency_field='currency_id')
    amount_total = fields.Monetary(
        compute='_compute_amounts', string='Total', currency_field='currency_id',
        help="Vista previa recalculada según los impuestos elegidos arriba. La "
             "factura nunca se modifica: el impuesto agregado se contabiliza como "
             "una línea aparte en el asiento de este pago.")
    amount_residual = fields.Monetary(
        compute='_compute_amounts', string='Cantidad por Pagar', currency_field='currency_id',
        help="Vista previa recalculada según los impuestos elegidos arriba. La "
             "factura nunca se modifica: el impuesto agregado se contabiliza como "
             "una línea aparte en el asiento de este pago.")
    allowed_tax_ids = fields.Many2many(
        'account.tax', compute='_compute_allowed_tax_ids',
        relation='account_payment_register_invoice_line_allowed_tax_rel',
        column1='invoice_line_id', column2='tax_id')
    tax_ids = fields.Many2many(
        'account.tax', string='Impuestos', inverse='_inverse_tax_ids',
        compute='_compute_tax_ids', store=True, readonly=False,
        relation='account_payment_register_invoice_line_tax_rel',
        column1='invoice_line_id', column2='tax_id',
        domain="[('id', 'in', allowed_tax_ids)]")
    # Set only via _inverse_tax_ids, i.e. only by a real user/API edit of
    # tax_ids -- never by _compute_tax_ids itself. Needed because the final
    # save of the wizard can re-touch move_id (unchanged in value) while
    # rebuilding withholding_invoice_ids, which would otherwise silently
    # reset tax_ids back to the invoice's original taxes (same class of bug
    # already seen with account.move.invoice_currency_rate).
    tax_ids_is_manual = fields.Boolean(copy=False)
    importe_is_manual = fields.Boolean(copy=False)
    importe = fields.Monetary(
        string='Importe', currency_field='currency_id',
        compute='_compute_importe', inverse='_inverse_importe',
        store=True, readonly=False,
        help="Cuánto se le va a abonar a esta factura en este pago. Con "
             "'Agrupar Pagos' activo se puede editar (nunca por encima de la "
             "Cantidad por Pagar); si no, siempre es igual a la Cantidad por "
             "Pagar completa.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        # The list widget's "editable" mode can submit a blank row (e.g. via
        # keyboard navigation past the last cell) even with create="0" on the
        # field/list. A row without move_id is never something our own code
        # produces on purpose, so drop it instead of hitting the DB's NOT
        # NULL constraint.
        vals_list = [vals for vals in vals_list if vals.get('move_id')]
        if not vals_list:
            return self.browse()
        return super().create(vals_list)

    @api.depends('move_id')
    def _compute_allowed_tax_ids(self):
        for line in self:
            move = line.move_id
            if not move:
                line.allowed_tax_ids = self.env['account.tax']
                continue
            candidates = self.env['account.tax']._get_withholding_candidate_taxes(
                company=move.company_id, move_type=move.move_type,
            )
            line.allowed_tax_ids = candidates | move.invoice_line_ids.tax_ids

    def _inverse_tax_ids(self):
        for line in self:
            line.tax_ids_is_manual = True

    @api.depends('move_id')
    def _compute_tax_ids(self):
        # Default: whatever taxes the invoice's lines currently carry. Only
        # ever supplies the STARTING value shown when a row is added to the
        # table -- once the user (or our own code) has set tax_ids for real
        # (tax_ids_is_manual), further recomputes must not touch it again.
        for line in self:
            if line.tax_ids_is_manual:
                continue
            line.tax_ids = line.move_id.invoice_line_ids.tax_ids

    @api.depends('tax_ids', 'move_id.amount_untaxed', 'move_id.amount_total', 'move_id.amount_residual')
    def _compute_amounts(self):
        AccountTax = self.env['account.tax']
        for line in self:
            move = line.move_id
            if not move:
                line.amount_total = 0.0
                line.amount_residual = 0.0
                continue
            if line.tax_ids == move.invoice_line_ids.tax_ids:
                # Nothing pending: show the invoice's real current values.
                line.amount_total = move.amount_total
                line.amount_residual = move.amount_residual
                continue

            # Live preview only: recompute what the total WOULD be with the
            # taxes currently selected, without touching the real invoice.
            base_line = AccountTax._prepare_base_line_for_taxes_computation(
                None, tax_ids=line.tax_ids, price_unit=move.amount_untaxed, quantity=1.0,
                currency_id=move.currency_id,
            )
            AccountTax._add_tax_details_in_base_line(base_line, move.company_id)
            AccountTax._round_base_lines_tax_details([base_line], move.company_id)
            tax_amount = sum(
                t['tax_amount_currency'] for t in base_line['tax_details']['taxes_data']
            )
            new_total = move.amount_untaxed + tax_amount
            already_settled = move.amount_total - move.amount_residual
            line.amount_total = new_total
            line.amount_residual = new_total - already_settled

    @api.depends('amount_residual', 'register_id.group_payment')
    def _compute_importe(self):
        for line in self:
            if not line.register_id.group_payment or not line.importe_is_manual:
                line.importe = line.amount_residual

    def _inverse_importe(self):
        for line in self:
            line.importe_is_manual = True

    @api.constrains('importe')
    def _check_importe(self):
        for line in self:
            if line.currency_id.compare_amounts(line.importe, 0) < 0:
                raise UserError(_(
                    "El importe de %s no puede ser negativo."
                ) % line.move_id.display_name)
            if line.currency_id.compare_amounts(line.importe, line.amount_residual) > 0:
                raise UserError(_(
                    "El importe de %(move)s (%(importe)s) no puede superar lo que "
                    "esa factura debe (%(residual)s)."
                ) % {
                    'move': line.move_id.display_name,
                    'importe': line.importe,
                    'residual': line.amount_residual,
                })

    def _get_added_taxes(self):
        """Impuestos elegidos en el wizard que no estaban ya en la factura --
        los únicos que deben generar una línea de retención en el asiento del
        pago (un impuesto que ya estaba en la factura no se debe duplicar)."""
        self.ensure_one()
        return self.tax_ids - self.move_id.invoice_line_ids.tax_ids

    def _get_added_tax_amounts(self, proration=1.0):
        """Para cada impuesto agregado (ver `_get_added_taxes`) calcula el
        monto y la cuenta contable que le correspondería si se aplicara sobre
        el valor sin impuesto de la factura, usando el motor de impuestos de
        Odoo (misma fuente de verdad que `_compute_amounts`, pero por
        impuesto individual en vez de la suma). `proration` prorratea el
        monto según qué fracción de la factura se paga ahora (pago parcial en
        un pago agrupado). El signo devuelto es el "signo factura" (negativo
        para una retención): quien lo consuma decide el signo final según la
        dirección del pago (entrante/saliente).

        :return: lista de dicts {'tax', 'account', 'amount_currency'}.
        """
        self.ensure_one()
        added_taxes = self._get_added_taxes()
        if not added_taxes:
            return []

        move = self.move_id
        AccountTax = self.env['account.tax']
        results = []
        for tax in added_taxes:
            base_line = AccountTax._prepare_base_line_for_taxes_computation(
                None, tax_ids=tax, price_unit=move.amount_untaxed, quantity=1.0,
                currency_id=move.currency_id,
            )
            AccountTax._add_tax_details_in_base_line(base_line, move.company_id)
            AccountTax._round_base_lines_tax_details([base_line], move.company_id)
            AccountTax._add_accounting_data_to_base_line_tax_details(base_line, move.company_id)
            for tax_data in base_line['tax_details']['taxes_data']:
                for tax_rep_data in tax_data['tax_reps_data']:
                    if not tax_rep_data['account']:
                        raise UserError(_(
                            "El impuesto '%s' no tiene una cuenta contable configurada "
                            "en su distribución de impuestos, así que no se puede usar "
                            "como retención dinámica en este pago. Configúrele una "
                            "cuenta en Contabilidad > Configuración > Impuestos."
                        ) % tax.name)
                    results.append({
                        'tax': tax,
                        'account': tax_rep_data['account'],
                        'amount_currency': tax_rep_data['tax_amount_currency'] * proration,
                    })
        return results
