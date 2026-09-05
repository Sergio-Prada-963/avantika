# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    aps_cron_interval_days = fields.Integer(
        related='company_id.aps_cron_interval_days', readonly=False)
    aps_due_days_ahead = fields.Integer(
        related='company_id.aps_due_days_ahead', readonly=False)
    aps_payment_journal_id = fields.Many2one(
        related='company_id.aps_payment_journal_id', readonly=False)

    def set_values(self):
        super().set_values()
        cron = self.env.ref(
            'account_payment_scheduler.ir_cron_generate_payment_schedules',
            raise_if_not_found=False,
        )
        if cron and self.aps_cron_interval_days:
            cron.write({
                'interval_number': self.aps_cron_interval_days,
                'interval_type': 'days',
            })
