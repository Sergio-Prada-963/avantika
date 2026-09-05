# -*- coding: utf-8 -*-
{
    'name': 'Cálculo de Listas de Precios de Venta',
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Cálculo de listas de precios de venta.',
    'description': """
Cálculo de Listas de Precios de Venta
======================================
Módulo base para el cálculo de listas de precios de venta.
""",
    'author': 'Sergio Rodriguez',
    'license': 'LGPL-3',
    'depends': [
        'sale',
        'account',
        'product',
        'contacts',
        'account_manual_currency_rate',
        'mrp',
    ],
    'data': [
        'views/res_partner_views.xml',
        'views/res_users_views.xml',
        'views/product_pricelist_views.xml',
        'views/product_supplierinfo_views.xml',
        'views/product_pricelist_item_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
