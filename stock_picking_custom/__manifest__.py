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
        'reports/stock_picking_report_templates.xml',
        'reports/stock_shipping_label_report_templates.xml',
        'reports/stock_picking_reports.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
