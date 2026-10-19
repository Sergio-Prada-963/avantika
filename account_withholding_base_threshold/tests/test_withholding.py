# -*- coding: utf-8 -*-
from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

UVT = 52374.0


@tagged('post_install', '-at_install')
class TestWithholdingBaseThreshold(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.company_data['company']
        company.uvt_value = UVT
        company.wbt_no_product_mode = 'exclude'
        cls.env.user.group_ids |= cls.env.ref('sales_team.group_sale_manager') | cls.env.ref('stock.group_stock_manager')

        co = cls.env.ref('base.co')
        City = cls.env['res.city']
        cls.baq = City.create({'name': 'Barranquilla WBT', 'country_id': co.id})
        cls.bog = City.create({'name': 'Bogotá WBT', 'country_id': co.id})
        cls.med = City.create({'name': 'Medellín WBT', 'country_id': co.id})

        Fpos = cls.env['account.fiscal.position']
        cls.fp_pjrc = Fpos.create({'name': 'PJ Régimen Común'})
        cls.fp_pnnr = Fpos.create({'name': 'PN no responsable'})
        cls.fp_gc = Fpos.create({'name': 'PJ GC no autorretenedor'})
        cls.fp_simple = Fpos.create({'name': 'SIMPLE'})

        cls.categ_hon = cls.env['product.category'].create({'name': 'Honorarios'})
        cls.categ_hon_child = cls.env['product.category'].create({
            'name': 'Honorarios legales', 'parent_id': cls.categ_hon.id})

        Tax = cls.env['account.tax']

        def tax(name, amount, use, **kw):
            vals = {'name': name, 'amount': amount, 'amount_type': 'percent',
                    'type_tax_use': use, 'company_id': company.id}
            vals.update(kw)
            return Tax.create(vals)

        # IVA (no gestionados por el módulo)
        cls.iva19_v = tax('IVA 19% V', 19, 'sale')
        cls.iva5_v = tax('IVA 5% V', 5, 'sale')
        cls.iva19_c = tax('IVA 19% C', 19, 'purchase')

        total10 = {'uvt_base': True, 'uvt_base_type': 'total', 'uvt_quantity': 10}
        total2 = {'uvt_base': True, 'uvt_base_type': 'total', 'uvt_quantity': 2}
        zero = {'uvt_base': True, 'uvt_base_type': 'total', 'uvt_quantity': 0}

        # Compras
        cls.rf25_c = tax('2.5% RteFte Dec C', -2.5, 'purchase', wbt_product_scope='goods',
                         fiscal_position_ids=[Command.set((cls.fp_pjrc | cls.fp_gc).ids)], **total10)
        cls.rf35_c = tax('3.5% RteFte NR C', -3.5, 'purchase', wbt_product_scope='goods',
                         fiscal_position_ids=[Command.set(cls.fp_pnnr.ids)], **total10)
        cls.rf4_c = tax('4% RteFte Serv C', -4, 'purchase', wbt_product_scope='service',
                        wbt_exclude_categ_ids=[Command.set(cls.categ_hon.ids)],
                        fiscal_position_ids=[Command.set((cls.fp_pjrc | cls.fp_gc).ids)], **total2)
        cls.hon11_c = tax('11% RteFte Hon PJ C', -11, 'purchase',
                          wbt_categ_ids=[Command.set(cls.categ_hon.ids)],
                          fiscal_position_ids=[Command.set((cls.fp_pjrc | cls.fp_gc).ids)], **zero)
        cls.ica_c_baq = tax('ReteICA C Barranquilla', -0.966, 'purchase', is_reteica=True,
                            city_id=cls.baq.id,
                            fiscal_position_ids=[Command.set((cls.fp_pjrc | cls.fp_gc).ids)])
        cls.ica_c_bog = tax('ReteICA C Bogotá', -0.414, 'purchase', is_reteica=True,
                            city_id=cls.bog.id,
                            fiscal_position_ids=[Command.set((cls.fp_pjrc | cls.fp_gc).ids)])

        # Ventas
        cls.rf25_v = tax('2.5% RteFte V', -2.5, 'sale', wbt_product_scope='goods',
                         fiscal_position_ids=[Command.set((cls.fp_pjrc | cls.fp_gc).ids)], **total10)
        cls.rf4_v = tax('4% RteFte Serv V', -4, 'sale', wbt_product_scope='service',
                        fiscal_position_ids=[Command.set((cls.fp_pjrc | cls.fp_gc).ids)], **total2)
        cls.reteiva19_v = tax('15% RteIVA 19% V', -2.85, 'sale',
                              wbt_required_tax_ids=[Command.set(cls.iva19_v.ids)],
                              fiscal_position_ids=[Command.set(cls.fp_gc.ids)], **total10)
        cls.reteiva5_v = tax('15% RteIVA 5% V', -0.75, 'sale',
                             wbt_required_tax_ids=[Command.set(cls.iva5_v.ids)],
                             fiscal_position_ids=[Command.set(cls.fp_gc.ids)], **total10)
        cls.ica_v_baq = tax('ReteICA V Barranquilla', -1.26, 'sale', is_reteica=True, city_id=cls.baq.id,
                            fiscal_position_ids=[Command.set((cls.fp_pjrc | cls.fp_gc).ids)])
        cls.ica_v_med = tax('ReteICA V Medellín', -0.8, 'sale', is_reteica=True, city_id=cls.med.id,
                            fiscal_position_ids=[Command.set((cls.fp_pjrc | cls.fp_gc).ids)])
        cls.autoret = tax('Autorretención 1,20%', 1.2, 'sale', **zero)

        cls.wbt_taxes = (cls.rf25_c | cls.rf35_c | cls.rf4_c | cls.hon11_c | cls.ica_c_baq | cls.ica_c_bog
                         | cls.rf25_v | cls.rf4_v | cls.reteiva19_v | cls.reteiva5_v | cls.ica_v_baq
                         | cls.ica_v_med | cls.autoret)

        Product = cls.env['product.product']
        cls.p_goods = Product.create({
            'name': 'Bien WBT', 'type': 'consu', 'invoice_policy': 'order',
            'taxes_id': [Command.set(cls.iva19_v.ids)],
            'supplier_taxes_id': [Command.set(cls.iva19_c.ids)]})
        cls.p_goods5 = Product.create({
            'name': 'Bien 5% WBT', 'type': 'consu', 'invoice_policy': 'order',
            'taxes_id': [Command.set(cls.iva5_v.ids)]})
        cls.p_service = Product.create({
            'name': 'Servicio WBT', 'type': 'service', 'invoice_policy': 'order',
            'taxes_id': [Command.set(cls.iva19_v.ids)],
            'supplier_taxes_id': [Command.set(cls.iva19_c.ids)]})
        cls.p_hon = Product.create({
            'name': 'Honorarios WBT', 'type': 'service', 'categ_id': cls.categ_hon_child.id,
            'supplier_taxes_id': [Command.set(cls.iva19_c.ids)]})

        # Bodegas
        cls.wh_baq = cls.env['stock.warehouse'].search([('company_id', '=', company.id)], limit=1)
        cls.wh_baq.partner_id = cls.env['res.partner'].create({'name': 'CEDI BAQ', 'city_id': cls.baq.id})
        cls.wh_bog = cls.env['stock.warehouse'].create({
            'name': 'CEDI Bogotá', 'code': 'BOG', 'company_id': company.id,
            'partner_id': cls.env['res.partner'].create({'name': 'CEDI BOG', 'city_id': cls.bog.id}).id,
        })

        Partner = cls.env['res.partner']
        cls.v_pjrc = Partner.create({'name': 'Prov PJ RC', 'is_company': True,
                                     'property_account_position_id': cls.fp_pjrc.id,
                                     'wbt_reteica_tax_ids': [Command.set((cls.ica_c_baq | cls.ica_c_bog).ids)]})
        cls.v_pnnr = Partner.create({'name': 'Prov PN NR', 'property_account_position_id': cls.fp_pnnr.id})
        cls.v_simple = Partner.create({'name': 'Prov SIMPLE', 'is_company': True,
                                       'property_account_position_id': cls.fp_simple.id})
        cls.c_pjrc = Partner.create({'name': 'Cli PJ RC agente', 'is_company': True, 'city_id': cls.baq.id,
                                     'property_account_position_id': cls.fp_pjrc.id,
                                     'wbt_reteica_agent': True})
        cls.c_pjrc_ship_med = Partner.create({'name': 'Entrega Medellín', 'parent_id': cls.c_pjrc.id,
                                              'type': 'delivery', 'city_id': cls.med.id})
        cls.c_pjrc_noagent = Partner.create({'name': 'Cli PJ RC no agente', 'is_company': True,
                                             'property_account_position_id': cls.fp_pjrc.id})
        cls.c_gc = Partner.create({'name': 'Cli GC', 'is_company': True,
                                   'property_account_position_id': cls.fp_gc.id, 'wbt_reteica_agent': True})
        cls.c_none = Partner.create({'name': 'Cli sin posición', 'is_company': True})

    # ------------------------------------------------------------------
    def _wbt(self, line):
        return line.tax_ids & self.wbt_taxes

    def _bill(self, partner, lines, move_type='in_invoice', **kw):
        vals = {
            'move_type': move_type,
            'partner_id': partner.id,
            'invoice_date': '2026-10-01',
            'invoice_line_ids': [Command.create(l) for l in lines],
        }
        vals.update(kw)
        return self.env['account.move'].create(vals)

    def _line(self, product, price, qty=1, **kw):
        vals = {'product_id': product.id, 'quantity': qty, 'price_unit': price}
        vals.update(kw)
        return vals

    def _so(self, partner, lines, **kw):
        vals = {
            'partner_id': partner.id,
            'warehouse_id': self.wh_baq.id,
            'order_line': [Command.create({'product_id': p.id, 'product_uom_qty': 1, 'price_unit': price})
                           for p, price in lines],
        }
        vals.update(kw)
        return self.env['sale.order'].create(vals)

    # ------------------------------------------------------------------
    # Posición fiscal (A1)
    # ------------------------------------------------------------------
    def test_p1_vendor_pjrc_goods(self):
        bill = self._bill(self.v_pjrc, [self._line(self.p_goods, 1000000)])
        self.assertEqual(self._wbt(bill.invoice_line_ids) - self.ica_c_baq - self.ica_c_bog, self.rf25_c)

    def test_p2_vendor_pn_no_responsable(self):
        bill = self._bill(self.v_pnnr, [self._line(self.p_goods, 1000000)])
        self.assertEqual(self._wbt(bill.invoice_line_ids), self.rf35_c)

    def test_p4_simple_no_withholding(self):
        bill = self._bill(self.v_simple, [self._line(self.p_service, 1000000)])
        self.assertFalse(self._wbt(bill.invoice_line_ids))

    def test_p5_no_fiscal_position_only_autoret(self):
        inv = self._bill(self.c_none, [self._line(self.p_goods, 1000000)], move_type='out_invoice')
        self.assertEqual(self._wbt(inv.invoice_line_ids), self.autoret)

    def test_p8_change_fiscal_position_recomputes(self):
        bill = self._bill(self.v_pjrc, [self._line(self.p_goods, 1000000)])
        self.assertIn(self.rf25_c, bill.invoice_line_ids.tax_ids)
        bill.fiscal_position_id = self.fp_pnnr
        self.assertNotIn(self.rf25_c, bill.invoice_line_ids.tax_ids)
        self.assertIn(self.rf35_c, bill.invoice_line_ids.tax_ids)

    # ------------------------------------------------------------------
    # Alcance por línea (A2, A6)
    # ------------------------------------------------------------------
    def test_l1_goods_and_service_split(self):
        bill = self._bill(self.v_pjrc, [self._line(self.p_goods, 1000000), self._line(self.p_service, 1000000)])
        goods, service = bill.invoice_line_ids
        self.assertIn(self.rf25_c, goods.tax_ids)
        self.assertNotIn(self.rf4_c, goods.tax_ids)
        self.assertIn(self.rf4_c, service.tax_ids)
        self.assertNotIn(self.rf25_c, service.tax_ids)

    def test_l2_honorarios_only_11(self):
        bill = self._bill(self.v_pjrc, [self._line(self.p_hon, 1000000)])
        taxes = bill.invoice_line_ids.tax_ids
        self.assertIn(self.hon11_c, taxes)
        self.assertNotIn(self.rf4_c, taxes)

    def test_l3_reteiva_by_vat_rate(self):
        inv = self._bill(self.c_gc, [self._line(self.p_goods, 1000000), self._line(self.p_goods5, 1000000)],
                         move_type='out_invoice')
        l19, l5 = inv.invoice_line_ids
        self.assertIn(self.reteiva19_v, l19.tax_ids)
        self.assertNotIn(self.reteiva5_v, l19.tax_ids)
        self.assertIn(self.reteiva5_v, l5.tax_ids)
        self.assertNotIn(self.reteiva19_v, l5.tax_ids)

    def test_l5_line_without_product(self):
        bill = self._bill(self.v_pjrc, [{'name': 'Gasto', 'quantity': 1, 'price_unit': 1000000}])
        self.assertFalse(self._wbt(bill.invoice_line_ids))
        self.company_data['company'].wbt_no_product_mode = 'service'
        bill.invoice_line_ids.price_unit = 1000001
        self.assertIn(self.rf4_c, bill.invoice_line_ids.tax_ids)

    def test_l6_sections_and_notes_untouched(self):
        bill = self._bill(self.v_pjrc, [
            {'display_type': 'line_section', 'name': 'Sección'},
            self._line(self.p_goods, 1000000),
            {'display_type': 'line_note', 'name': 'Nota'},
        ])
        for line in bill.invoice_line_ids.filtered(lambda l: l.display_type != 'product'):
            self.assertFalse(line.tax_ids)
        self.assertIn(self.rf25_c, bill.invoice_line_ids.filtered(lambda l: l.display_type == 'product').tax_ids)

    # ------------------------------------------------------------------
    # Base UVT (A3, A5)
    # ------------------------------------------------------------------
    def test_u1_u2_exact_threshold(self):
        bill = self._bill(self.v_pjrc, [self._line(self.p_goods, 523740)])
        self.assertIn(self.rf25_c, bill.invoice_line_ids.tax_ids)
        bill = self._bill(self.v_pjrc, [self._line(self.p_goods, 523739)])
        self.assertNotIn(self.rf25_c, bill.invoice_line_ids.tax_ids)

    def test_u3_service_threshold(self):
        bill = self._bill(self.v_pjrc, [self._line(self.p_service, 104748)])
        self.assertIn(self.rf4_c, bill.invoice_line_ids.tax_ids)
        bill = self._bill(self.v_pjrc, [self._line(self.p_service, 104747)])
        self.assertNotIn(self.rf4_c, bill.invoice_line_ids.tax_ids)

    def test_u4_two_goods_sum(self):
        bill = self._bill(self.v_pjrc, [self._line(self.p_goods, 400000), self._line(self.p_goods, 200000)])
        for line in bill.invoice_line_ids:
            self.assertIn(self.rf25_c, line.tax_ids)

    def test_u5_goods_base_excludes_service(self):
        bill = self._bill(self.v_pjrc, [self._line(self.p_goods, 400000), self._line(self.p_service, 200000)])
        goods, service = bill.invoice_line_ids
        self.assertNotIn(self.rf25_c, goods.tax_ids)
        self.assertIn(self.rf4_c, service.tax_ids)

    def test_u6_honorarios_zero_uvt(self):
        bill = self._bill(self.v_pjrc, [self._line(self.p_hon, 50000)])
        self.assertIn(self.hon11_c, bill.invoice_line_ids.tax_ids)

    def test_u7_foreign_currency_converted(self):
        # 1 moneda compañía = 2 moneda extranjera (tasa 2017+)
        other = self.setup_other_currency('EUR')
        bill = self._bill(self.v_pjrc, [self._line(self.p_goods, 1000000)], currency_id=other.id)
        # 1.000.000 EUR = 500.000 en moneda compañía < 523.740
        self.assertNotIn(self.rf25_c, bill.invoice_line_ids.tax_ids)
        bill.invoice_line_ids.price_unit = 1200000  # = 600.000
        self.assertIn(self.rf25_c, bill.invoice_line_ids.tax_ids)

    def test_u9_uvt_zero_module_inactive(self):
        self.company_data['company'].uvt_value = 0
        bill = self._bill(self.v_pjrc, [self._line(self.p_goods, 1000000, tax_ids=[Command.set(self.rf35_c.ids)])])
        self.assertEqual(bill.invoice_line_ids.tax_ids, self.rf35_c)

    def test_a5_constraint_allows_zero(self):
        self.rf25_c.uvt_quantity = 0
        with self.assertRaises(ValidationError):
            self.rf25_c.uvt_quantity = -1

    def test_autoret_small_amount(self):
        inv = self._bill(self.c_pjrc_noagent, [self._line(self.p_goods, 1000)], move_type='out_invoice')
        self.assertIn(self.autoret, inv.invoice_line_ids.tax_ids)
        self.assertNotIn(self.rf25_v, inv.invoice_line_ids.tax_ids)

    # ------------------------------------------------------------------
    # ReteICA ventas (A4)
    # ------------------------------------------------------------------
    def test_i1_i2_reteica_agent(self):
        so = self._so(self.c_pjrc, [(self.p_goods, 1000000)])
        self.assertIn(self.ica_v_baq, so.order_line.tax_ids)
        so = self._so(self.c_pjrc_noagent, [(self.p_goods, 1000000)])
        self.assertFalse(so.order_line.tax_ids & (self.ica_v_baq | self.ica_v_med))

    def test_i7_i9_reteica_per_line_and_invoice(self):
        so = self._so(self.c_pjrc, [(self.p_goods, 1000000), (self.p_service, 1000000)],
                      partner_shipping_id=self.c_pjrc_ship_med.id)
        goods, service = so.order_line
        self.assertIn(self.ica_v_baq, goods.tax_ids)
        self.assertNotIn(self.ica_v_med, goods.tax_ids)
        self.assertIn(self.ica_v_med, service.tax_ids)
        self.assertNotIn(self.ica_v_baq, service.tax_ids)
        so.action_confirm()
        inv = so._create_invoices()
        for so_line in so.order_line:
            inv_line = inv.invoice_line_ids.filtered(lambda l: so_line in l.sale_line_ids)
            self.assertEqual(self._wbt(inv_line), self._wbt(so_line))

    def test_i8_forced_city(self):
        so = self._so(self.c_pjrc, [(self.p_goods, 1000000)])
        so.city_declaration_id = self.med
        self.assertIn(self.ica_v_med, so.order_line.tax_ids)
        self.assertNotIn(self.ica_v_baq, so.order_line.tax_ids)

    def test_i10_direct_invoice_goods_no_order(self):
        inv = self._bill(self.c_pjrc, [self._line(self.p_goods, 1000000)], move_type='out_invoice')
        self.assertFalse(inv.invoice_line_ids.tax_ids & (self.ica_v_baq | self.ica_v_med))
        inv.city_declaration_id = self.baq
        self.assertIn(self.ica_v_baq, inv.invoice_line_ids.tax_ids)

    # ------------------------------------------------------------------
    # ReteICA compras (A4)
    # ------------------------------------------------------------------
    def _po(self, partner, warehouse, lines):
        return self.env['purchase.order'].create({
            'partner_id': partner.id,
            'picking_type_id': warehouse.in_type_id.id,
            'order_line': [Command.create({'product_id': p.id, 'product_qty': 1, 'price_unit': price})
                           for p, price in lines],
        })

    def test_ic1_ic2_purchase_reteica_by_receiving_warehouse(self):
        po = self._po(self.v_pjrc, self.wh_baq, [(self.p_goods, 1000000)])
        self.assertIn(self.ica_c_baq, po.order_line.tax_ids)
        self.assertNotIn(self.ica_c_bog, po.order_line.tax_ids)
        po.picking_type_id = self.wh_bog.in_type_id
        self.assertIn(self.ica_c_bog, po.order_line.tax_ids)
        self.assertNotIn(self.ica_c_baq, po.order_line.tax_ids)

    def test_ic_vendor_without_rates(self):
        po = self._po(self.v_pnnr, self.wh_baq, [(self.p_goods, 1000000)])
        self.assertFalse(po.order_line.tax_ids & (self.ica_c_baq | self.ica_c_bog))

    # ------------------------------------------------------------------
    # Flujos (A7, A8, A9)
    # ------------------------------------------------------------------
    def test_f3_credit_note_keeps_withholdings(self):
        bill = self._bill(self.v_pjrc, [self._line(self.p_goods, 1000000)])
        bill.action_post()
        refund = bill._reverse_moves()
        self.assertEqual(refund.reversed_entry_id, bill)
        refund.invoice_line_ids.price_unit = 100000
        self.assertIn(self.rf25_c, refund.invoice_line_ids.tax_ids)

    def test_f5_change_partner_draft(self):
        bill = self._bill(self.v_pjrc, [self._line(self.p_goods, 1000000)])
        bill.write({'partner_id': self.v_pnnr.id, 'fiscal_position_id': self.fp_pnnr.id})
        self.assertIn(self.rf35_c, bill.invoice_line_ids.tax_ids)
        self.assertNotIn(self.rf25_c, bill.invoice_line_ids.tax_ids)

    def test_f6_posted_invoice_untouched(self):
        bill = self._bill(self.v_pjrc, [self._line(self.p_goods, 1000000)])
        bill.action_post()
        self.company_data['company'].uvt_value = 999999
        bill._wbt_sync_withholding_taxes()
        self.assertIn(self.rf25_c, bill.invoice_line_ids.tax_ids)

    def test_f8_locked_order_untouched(self):
        so = self._so(self.c_pjrc, [(self.p_goods, 1000000)])
        so.action_confirm()
        so.action_lock()
        self.company_data['company'].uvt_value = 999999
        so._wbt_sync_withholding_taxes()
        self.assertIn(self.rf25_v, so.order_line.tax_ids)

    def test_sale_onchange_form(self):
        from odoo.tests import Form
        with Form(self.env['sale.order']) as so_form:
            so_form.partner_id = self.c_pjrc
            so_form.warehouse_id = self.wh_baq
            with so_form.order_line.new() as line:
                line.product_id = self.p_goods
                line.price_unit = 1000000
        so = so_form.save()
        self.assertIn(self.rf25_v, so.order_line.tax_ids)
        self.assertIn(self.ica_v_baq, so.order_line.tax_ids)
