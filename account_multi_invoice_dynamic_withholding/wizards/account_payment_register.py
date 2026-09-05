# -*- coding: utf-8 -*-
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError

RECEIVABLE_PAYABLE_TYPES = ('asset_receivable', 'liability_payable')


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    withholding_invoice_ids = fields.One2many(
        'account.payment.register.invoice.line', 'register_id', string='Facturas')
    withholding_invoice_move_ids = fields.Many2many(
        'account.move', compute='_compute_withholding_helper_fields')
    withholding_partner_id = fields.Many2one(
        'res.partner', compute='_compute_withholding_helper_fields')
    add_move_id = fields.Many2one(
        'account.move', string='Agregar Factura',
        # Solo facturas (nunca notas crédito), y del tipo que corresponde al
        # lado del wizard en el que se abrió: si es un pago a un cliente, solo
        # facturas de cliente; si es a un proveedor, solo facturas de proveedor.
        domain="[('id', 'not in', withholding_invoice_move_ids), "
               "('partner_id', '=', withholding_partner_id), "
               "('move_type', '=', 'out_invoice' if partner_type == 'customer' else 'in_invoice'), "
               "('state', '=', 'posted'), "
               "('payment_state', 'not in', ('paid', 'reversed', 'in_payment'))]")

    @api.depends('withholding_invoice_ids.move_id')
    def _compute_withholding_helper_fields(self):
        for register in self:
            register.withholding_invoice_move_ids = register.withholding_invoice_ids.move_id
            register.withholding_partner_id = (
                register.withholding_invoice_ids[:1].partner_id or register.partner_id
            )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'withholding_invoice_ids' not in fields_list:
            return res

        line_ids = self._extract_ids_from_command(res.get('line_ids'))
        moves = self.env['account.move.line'].browse(line_ids).move_id
        if len(moves.partner_id) > 1:
            raise UserError(_(
                "Esta funcionalidad no admite registrar el pago de facturas de "
                "distintos terceros a la vez: %s. Selecciónelas por separado."
            ) % ', '.join(moves.partner_id.mapped('display_name')))
        res['withholding_invoice_ids'] = [Command.create({'move_id': move.id}) for move in moves]
        return res

    @staticmethod
    def _extract_ids_from_command(commands):
        ids = []
        for command in commands or []:
            if command[0] == Command.SET:
                ids.extend(command[2])
            elif command[0] == Command.LINK:
                ids.append(command[1])
        return ids

    @api.onchange('add_move_id')
    def _onchange_add_move_id(self):
        for register in self:
            move = register.add_move_id
            if not move:
                continue
            register.add_move_id = False

            if move.id in register.withholding_invoice_ids.move_id.ids:
                continue
            if register.withholding_invoice_ids and move.partner_id != register.withholding_invoice_ids[0].partner_id:
                return {'warning': {
                    'title': _("Tercero distinto"),
                    'message': _(
                        "Todas las facturas del pago deben ser del mismo tercero. "
                        "%(move)s pertenece a %(partner)s.",
                        move=move.display_name, partner=move.partner_id.display_name,
                    ),
                }}
            if move.currency_id != register.currency_id:
                return {'warning': {
                    'title': _("Moneda distinta"),
                    'message': _(
                        "%(move)s está en %(move_currency)s y el pago está en %(payment_currency)s. "
                        "Solo se pueden agregar facturas en la misma moneda del pago.",
                        move=move.display_name, move_currency=move.currency_id.name,
                        payment_currency=register.currency_id.name,
                    ),
                }}
            if move.company_id != register.company_id:
                return {'warning': {
                    'title': _("Compañía distinta"),
                    'message': _(
                        "%(move)s pertenece a la compañía %(move_company)s, distinta a la del "
                        "pago (%(payment_company)s).",
                        move=move.display_name, move_company=move.company_id.name,
                        payment_company=register.company_id.name,
                    ),
                }}

            register.withholding_invoice_ids = [Command.create({'move_id': move.id})]
            register._sync_line_ids_from_withholding_invoices()

    @api.onchange('withholding_invoice_ids')
    def _onchange_withholding_invoice_ids(self):
        for register in self:
            register._sync_line_ids_from_withholding_invoices()

    @api.onchange('withholding_invoice_ids.importe', 'withholding_invoice_ids.tax_ids')
    def _onchange_withholding_importe_live(self):
        # Keep `amount` in sync with what will actually be paid -- the sum of
        # each row's `importe` PLUS whatever tax was dynamically added to it
        # (never the max possible `amount_residual`) -- as the user edits,
        # instead of waiting until confirm. Must be declared on this model
        # (not from the child row's own onchange) -- `self` here is reliably
        # the wizard; a child row's `register_id` is not guaranteed to be
        # populated inside its own onchange dispatch.
        for register in self:
            if not register.withholding_invoice_ids:
                continue
            new_total = register._compute_total_amount_to_pay()
            if register.currency_id.is_zero(register.amount - new_total):
                continue
            # `_compute_amount` silently recomputes `amount` from
            # `source_amount` on its next trigger unless `custom_user_amount`
            # is also set -- both must be written together for the value to
            # actually stick and show up in the form.
            register.custom_user_amount = new_total
            register.amount = new_total

    def _get_rows_to_pay(self):
        """Filas de `withholding_invoice_ids` que efectivamente se van a
        pagar en esta pasada (importe en 0 = se excluye del pago sin
        quitarla de la tabla)."""
        self.ensure_one()
        return self.withholding_invoice_ids.filtered(
            lambda l: l.currency_id.compare_amounts(l.importe, 0) > 0
        )

    def _compute_total_amount_to_pay(self):
        """Suma, sobre las filas a pagar, de `importe` + la magnitud de
        cualquier impuesto agregado dinámicamente (prorrateado si el importe
        es menor a la cantidad por pagar de esa factura). Este es el valor
        que debe llevar el campo `amount` del pago para que la contrapartida
        cierre exactamente contra lo que cada factura realmente debe."""
        self.ensure_one()
        total = 0.0
        for row in self._get_rows_to_pay():
            proration = row.importe / row.amount_residual if row.amount_residual else 0.0
            tax_magnitude = sum(
                abs(added['amount_currency'])
                for added in row._get_added_tax_amounts(proration=proration)
            )
            total += row.importe + tax_magnitude
        return total

    def _sync_line_ids_from_withholding_invoices(self):
        self.ensure_one()
        moves = self.withholding_invoice_ids.move_id
        lines = moves.line_ids.filtered(
            lambda l: l.account_id.account_type in RECEIVABLE_PAYABLE_TYPES and not l.reconciled
        )
        if not lines:
            # Never blank out line_ids: the native _compute_batches hard-fails
            # ("...without at least one receivable/payable line") the instant
            # line_ids becomes empty. If there's nothing to sync to, leave
            # whatever line_ids already has rather than break the wizard.
            return
        if set(self.line_ids._origin.ids) == set(lines._origin.ids):
            # Nothing actually changed (e.g. this ran because the user only
            # edited `importe`/`tax_ids` on a row, not the set of invoices).
            # Writing the same ids again would still mark `line_ids` as
            # touched, which cascades into a spurious recompute of
            # `can_edit_wizard` (`@api.depends('line_ids')`) and, through it,
            # `group_payment` (`@api.depends('can_edit_wizard')`) -- wiping
            # out the user's manual toggle and, with it, `importe` (which
            # resets to `amount_residual` when `group_payment` is False).
            return
        self.line_ids = [Command.set(lines.ids)]

    def action_create_payments(self):
        for register in self:
            register._check_withholding_single_partner()
        return super().action_create_payments()

    def _check_withholding_single_partner(self):
        self.ensure_one()
        partners = self.withholding_invoice_ids.partner_id
        if len(partners) > 1:
            raise UserError(_(
                "No se pueden pagar facturas de distintos terceros en el mismo "
                "registro de pago: %s"
            ) % ', '.join(partners.mapped('display_name')))

    # -------------------------------------------------------------------
    # Líneas dinámicas del asiento (contrapartida por factura + retención
    # por impuesto agregado), sin tocar nunca la factura original.
    # -------------------------------------------------------------------

    def _make_withholding_line_vals(self, row, added_tax):
        """Vals de account.payment.dynamic.line (kind='withholding') para un
        impuesto agregado dinámicamente sobre `row`. El signo depende de la
        dirección del pago: positivo (débito) si es entrante, negativo
        (crédito) si es saliente -- ver el análisis de signos en el plan."""
        self.ensure_one()
        magnitude = abs(added_tax['amount_currency'])
        sign = 1 if self.payment_type == 'inbound' else -1
        amount_currency = magnitude * sign
        return Command.create({
            'kind': 'withholding',
            'move_id': row.move_id.id,
            'tax_id': added_tax['tax'].id,
            'account_id': added_tax['account'].id,
            'partner_id': row.partner_id.id,
            'currency_id': self.currency_id.id,
            'amount_currency': amount_currency,
            'balance': self.currency_id._convert(
                amount_currency, self.company_id.currency_id, self.company_id, self.payment_date,
            ),
            'name': _("Retención %(tax)s - %(move)s", tax=added_tax['tax'].name, move=row.move_id.name),
        })

    def _make_counterpart_line_vals(self, row, tax_magnitude):
        """Vals de account.payment.dynamic.line (kind='counterpart') para la
        parte de `row` que se concilia contra la factura real: lo que se
        abona en efectivo (`importe`) más lo retenido (`tax_magnitude`), con
        el signo que corresponde para cerrar exactamente esa cuenta
        (crédito/-monto si es entrante, débito/+monto si es saliente)."""
        self.ensure_one()
        receivable_line = self.line_ids.filtered(lambda l: l.move_id == row.move_id)[:1]
        sign = -1 if self.payment_type == 'inbound' else 1
        amount_currency = (row.importe + tax_magnitude) * sign
        return Command.create({
            'kind': 'counterpart',
            'move_id': row.move_id.id,
            'account_id': receivable_line.account_id.id,
            'partner_id': row.partner_id.id,
            'currency_id': self.currency_id.id,
            'amount_currency': amount_currency,
            'balance': self.currency_id._convert(
                amount_currency, self.company_id.currency_id, self.company_id, self.payment_date,
            ),
            'name': row.move_id.payment_reference or row.move_id.name,
        })

    def _create_payment_vals_from_wizard(self, batch_result):
        # EXTENDS account: caso de un único pago agrupado para varias
        # facturas (group_payment=True). Reparte la contrapartida en una
        # línea por factura y agrega una línea de retención por cada
        # impuesto agregado dinámicamente, sin tocar las facturas.
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        if not self.group_payment:
            return payment_vals

        rows = self._get_rows_to_pay()
        if not rows:
            return payment_vals

        dynamic_line_ids = []
        total_amount = 0.0
        for row in rows:
            proration = row.importe / row.amount_residual if row.amount_residual else 0.0
            added_taxes = row._get_added_tax_amounts(proration=proration)
            tax_magnitude = sum(abs(added['amount_currency']) for added in added_taxes)

            dynamic_line_ids.append(self._make_counterpart_line_vals(row, tax_magnitude))
            for added_tax in added_taxes:
                dynamic_line_ids.append(self._make_withholding_line_vals(row, added_tax))

            total_amount += row.importe + tax_magnitude

        payment_vals['dynamic_line_ids'] = dynamic_line_ids
        payment_vals['amount'] = total_amount
        return payment_vals

    def _create_payment_vals_from_batch(self, batch_result):
        # EXTENDS account: caso de un pago por factura (group_payment=False,
        # ya es un pago exclusivo por cada factura). Solo hace falta agregar
        # la(s) línea(s) de retención de esa factura; la contrapartida ya es
        # una sola línea = esa única factura, el comportamiento nativo ya es
        # el correcto.
        payment_vals = super()._create_payment_vals_from_batch(batch_result)
        moves = batch_result['lines'].move_id
        rows = self.withholding_invoice_ids.filtered(lambda l: l.move_id in moves)
        if not rows:
            return payment_vals

        dynamic_line_ids = []
        for row in rows:
            for added_tax in row._get_added_tax_amounts(proration=1.0):
                dynamic_line_ids.append(self._make_withholding_line_vals(row, added_tax))

        if dynamic_line_ids:
            payment_vals['dynamic_line_ids'] = dynamic_line_ids
        return payment_vals
