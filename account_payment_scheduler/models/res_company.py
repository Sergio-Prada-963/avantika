# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    aps_cron_interval_days = fields.Integer(
        string="Frecuencia de Generación (días)",
        default=1,
        help="Cada cuántos días se genera automáticamente una nueva "
             "programación de pago a proveedores.",
    )
    aps_due_days_ahead = fields.Integer(
        string="Días de Anticipación antes del Vencimiento",
        default=5,
        help="Número de días antes de la fecha de vencimiento de una "
             "factura de proveedor a partir de los cuales se incluye "
             "automáticamente en una programación de pago. Ej: 5 significa "
             "que se toman facturas que vencen en 5 días o menos.",
    )
    aps_payment_journal_id = fields.Many2one(
        'account.journal',
        string="Diario de Pago (Programación de Pagos)",
        domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', id)]",
        help="Diario usado por defecto para los pagos generados por las "
             "programaciones de pago a proveedores.",
    )
