# -*- coding: utf-8 -*-
{
    'name': 'Personalización de Transferencias de Inventario',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Reemplaza el PDF estándar de entrega por un formato propio.',
    'description': """
Personalización de Transferencias de Inventario
=================================================
Reemplaza el reporte "Delivery Slip" estándar de Odoo por una plantilla
propia (mismo contenido de datos que el reporte "Operaciones de
recolección"), tanto en el botón "Print" del formulario de transferencia
como en el menú genérico de impresión.
""",
    'author': 'Sergio Rodriguez',
    'license': 'LGPL-3',
    'depends': [
        'stock',
        'sale_stock',
        'product_expiry',
        'sale_order_custom',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        'reports/stock_picking_report_templates.xml',
        'reports/stock_shipping_label_report_templates.xml',
        'reports/stock_quant_count_report_templates.xml',
        'reports/stock_picking_reports.xml',
        'data/ir_cron_move_indicator.xml',
        'views/stock_picking_views.xml',
        'wizard/stock_move_change_picking_type_wizard_views.xml',
        'wizard/stock_move_create_internal_transfer_wizard_views.xml',
        'views/stock_move_pending_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'stock_picking_custom/static/src/scss/move_indicator.scss',
            'stock_picking_custom/static/src/widgets/product_location_qty_tags.js',
            'stock_picking_custom/static/src/widgets/product_location_qty_tags.xml',
            'stock_picking_custom/static/src/widgets/move_days_badge_field.js',
            'stock_picking_custom/static/src/widgets/move_days_badge_field.xml',
            'stock_picking_custom/static/src/views/move_dashboard.js',
            'stock_picking_custom/static/src/views/move_dashboard.xml',
            'stock_picking_custom/static/src/views/move_listview.js',
            'stock_picking_custom/static/src/views/move_listview.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
