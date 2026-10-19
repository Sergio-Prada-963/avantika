# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import Command, fields, models
from odoo.tools import float_compare


LINE_TRIGGER_FIELDS = {
    'product_id', 'price_unit', 'quantity', 'product_uom_qty', 'product_qty',
    'discount', 'tax_ids', 'display_type',
}


class WbtWithholdingMixin(models.AbstractModel):
    """A10: lógica común de retenciones para factura, cotización y orden de compra.

    Cada modelo que hereda debe tener: company_id, currency_id, partner_id,
    fiscal_position_id, y líneas con product_id, price_subtotal y tax_ids.
    Debe implementar los métodos marcados como "a implementar".
    """
    _name = 'wbt.withholding.mixin'
    _description = 'Retenciones automáticas por base UVT (mixin)'

    # ------------------------------------------------------------------
    # A implementar en cada modelo
    # ------------------------------------------------------------------
    def _wbt_type_tax_use(self):
        raise NotImplementedError

    def _wbt_is_editable(self):
        raise NotImplementedError

    def _wbt_lines(self):
        raise NotImplementedError

    def _wbt_lines_field(self):
        raise NotImplementedError

    def _wbt_date(self):
        return fields.Date.context_today(self)

    def _wbt_line_city(self, line, kind):
        """Ciudad de la operación de la línea (para ReteICA)."""
        return self.env['res.city']

    # ------------------------------------------------------------------
    # Comunes
    # ------------------------------------------------------------------
    def _wbt_sync_from_lines(self, lines, vals=None):
        """Recalcula los documentos de unas líneas editadas directamente
        (importaciones, código, edición en lista)."""
        if self.env.context.get('wbt_skip_sync'):
            return
        if vals is not None and not (LINE_TRIGGER_FIELDS & set(vals)):
            return
        self._wbt_sync_withholding_taxes()

    def _wbt_line_kind(self, product, no_product_mode):
        if product:
            return 'service' if product.type == 'service' else 'goods'
        return no_product_mode if no_product_mode in ('goods', 'service') else False

    def _wbt_reteica_allowed(self, tax):
        """Ventas: el cliente debe tener 'Me retiene ICA'.
        Compras: la tarifa debe estar en 'Tarifas ReteICA' del proveedor."""
        partner = self.partner_id.commercial_partner_id
        if self._wbt_type_tax_use() == 'sale':
            return bool(partner.wbt_reteica_agent)
        return tax._origin in partner.wbt_reteica_tax_ids._origin

    def _wbt_to_company_currency(self, amount, date):
        """A3: la base se compara en la moneda de la compañía."""
        company = self.company_id
        currency = self.currency_id or company.currency_id
        if not currency or currency == company.currency_id:
            return amount
        if isinstance(date, datetime):
            date = date.date()
        return currency._convert(amount, company.currency_id, company, date or fields.Date.context_today(self))

    def _wbt_sync_withholding_taxes(self):
        if self.env.context.get('wbt_skip_sync'):
            return
        Tax = self.env['account.tax']
        for doc in self:
            if not doc._wbt_is_editable():  # A8 / A9
                continue
            company = doc.company_id
            uvt_value = company.uvt_value
            if uvt_value <= 0:
                # Sin Valor UVT el módulo no toca los impuestos (U9).
                continue
            lines = doc._wbt_lines()  # A6: solo líneas de producto
            if not lines:
                continue
            managed = Tax.search(Tax._wbt_managed_domain(company, doc._wbt_type_tax_use()))
            if not managed:
                continue

            fpos = doc.fiscal_position_id
            no_product_mode = company.wbt_no_product_mode or 'exclude'
            date = doc._wbt_date()
            rounding = company.currency_id.rounding or 0.01

            info = []
            for line in lines:
                current = line.tax_ids._origin
                kind = doc._wbt_line_kind(line.product_id, no_product_mode)
                info.append({
                    'line': line,
                    'current': current,
                    'base_taxes': current - managed,
                    'product': line.product_id,
                    'kind': kind,
                    'city': doc._wbt_line_city(line, kind)._origin,
                    'amount': doc._wbt_to_company_currency(line.price_subtotal, date),
                    'desired': Tax,
                })

            for tax in managed:
                if not tax._wbt_applies_to_fpos(fpos):  # A1
                    continue
                if tax.is_reteica and not doc._wbt_reteica_allowed(tax):
                    continue
                eligible = [
                    li for li in info
                    if tax._wbt_line_in_scope(li['product'], li['base_taxes'], no_product_mode)  # A2
                    and (not tax.is_reteica or (li['city'] and li['city'] == tax.city_id))  # A4
                ]
                if not eligible:
                    continue
                if tax.uvt_base and tax.uvt_quantity > 0:  # A5: 0 UVT = aplica siempre
                    minimum = tax.uvt_quantity * uvt_value
                    if tax.uvt_base_type == 'total':
                        # A3: solo las líneas a las que aplica (y mismo municipio en ReteICA)
                        base = sum(li['amount'] for li in eligible)
                        if float_compare(base, minimum, precision_rounding=rounding) < 0:
                            eligible = []
                    else:
                        eligible = [
                            li for li in eligible
                            if float_compare(li['amount'], minimum, precision_rounding=rounding) >= 0
                        ]
                for li in eligible:
                    li['desired'] |= tax

            # A10: una sola escritura con el conjunto final de impuestos
            commands = []
            for li in info:
                new_taxes = li['base_taxes'] | li['desired']
                if set(new_taxes.ids) == set(li['current'].ids):
                    continue
                line = li['line']
                if not isinstance(line.id, int):
                    line.tax_ids = new_taxes  # onchange
                else:
                    commands.append(Command.update(line.id, {'tax_ids': [Command.set(new_taxes.ids)]}))
            if commands:
                doc.with_context(wbt_skip_sync=True).write({doc._wbt_lines_field(): commands})
