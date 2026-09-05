from odoo import _, api, fields, models
from odoo.exceptions import UserError

MOVE_TYPE_PARTNER_TYPE = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'out_receipt': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
    'in_receipt': 'supplier',
}


class AccountAdvancePaymentApply(models.TransientModel):
    _name = 'account.advance.payment.apply'
    _description = 'Aplicar Anticipos a Factura(s)'

    move_ids = fields.Many2many('account.move', string="Facturas", readonly=True)
    partner_id = fields.Many2one('res.partner', string="Tercero", readonly=True)
    partner_type = fields.Selection([('customer', 'Cliente'), ('supplier', 'Proveedor')], readonly=True)
    currency_id = fields.Many2one('res.currency', string="Moneda", readonly=True)
    invoice_residual = fields.Monetary(string="Saldo Pendiente de Facturas", currency_field='currency_id', readonly=True)
    advance_line_ids = fields.Many2many(
        'account.move.line',
        string="Anticipos a Aplicar",
        domain="[('id', 'in', available_advance_line_ids)]",
        required=True,
    )
    available_advance_line_ids = fields.Many2many('account.move.line', compute='_compute_available_advance_line_ids')

    @api.depends('partner_id', 'partner_type')
    def _compute_available_advance_line_ids(self):
        for wizard in self:
            if not wizard.partner_id:
                wizard.available_advance_line_ids = False
                continue
            balance_operator = '<' if wizard.partner_type == 'customer' else '>'
            domain = [
                ('account_id.apm_advance_account', '=', True),
                ('parent_state', '=', 'posted'),
                ('partner_id', '=', wizard.partner_id.id),
                ('reconciled', '=', False),
                ('balance', balance_operator, 0.0),
                '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0),
            ]
            wizard.available_advance_line_ids = self.env['account.move.line'].search(domain)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        context = self.env.context
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')
        if active_model != 'account.move' or not active_ids:
            return res

        moves = self.env['account.move'].browse(active_ids)
        if any(move.state != 'posted' for move in moves):
            raise UserError(_("You can only apply advance payments to posted invoices."))
        if any(move.partner_id != moves[0].partner_id for move in moves):
            raise UserError(_("All selected invoices must belong to the same partner."))
        if any(MOVE_TYPE_PARTNER_TYPE.get(move.move_type) != MOVE_TYPE_PARTNER_TYPE.get(moves[0].move_type) for move in moves):
            raise UserError(_("You cannot mix customer invoices and vendor bills in the same application."))
        if any(move.currency_id != moves[0].currency_id for move in moves):
            raise UserError(_("All selected invoices must share the same currency."))

        res.update({
            'move_ids': [(6, 0, moves.ids)],
            'partner_id': moves[0].partner_id.id,
            'partner_type': MOVE_TYPE_PARTNER_TYPE.get(moves[0].move_type),
            'currency_id': moves[0].currency_id.id,
            'invoice_residual': sum(moves.mapped('amount_residual')),
        })
        return res

    def action_apply(self):
        self.ensure_one()
        for move in self.move_ids.sorted('invoice_date'):
            if move.currency_id.is_zero(move.amount_residual):
                continue
            for line in self.advance_line_ids.sorted('date'):
                if move.currency_id.is_zero(move.amount_residual):
                    break
                if line.currency_id:
                    line_residual = abs(line.amount_residual_currency)
                else:
                    line_residual = abs(line.amount_residual)
                if (line.currency_id or line.company_currency_id).is_zero(line_residual):
                    continue
                move._apm_legalize_advance(line)
        return {'type': 'ir.actions.act_window_close'}
