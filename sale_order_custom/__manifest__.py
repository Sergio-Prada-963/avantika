# -*- coding: utf-8 -*-
{
    'name': 'Personalizaciones de Órdenes de Venta',
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Funcionalidades y ajustes personalizados sobre la orden de venta.',
    'description': """
Personalizaciones de Órdenes de Venta
======================================
Módulo base para agregar campos, vistas y lógica personalizada sobre
sale.order y sale.order.line sin modificar el módulo estándar de ventas.
""",
    'author': 'Sergio Rodriguez',
    'license': 'LGPL-3',
    'depends': [
        'sale',
        'sale_stock',
        'sale_margin',
        'sale_management',
        'mrp',
        'mrp_account',
        'price_list_sales',
        'analytic',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/sale_order_change_product_wizard_views.xml',
        'views/mrp_bom_views.xml',
        'views/product_supplierinfo_views.xml',
        'views/sale_order_views.xml',
        'views/res_users_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sale_order_custom/static/src/widgets/stock_quant_search_widget.js',
            'sale_order_custom/static/src/widgets/stock_quant_search_widget.xml',
            'sale_order_custom/static/src/scss/sale_order_line_margin.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
