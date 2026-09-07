# -*- coding: utf-8 -*-
{
    'name': 'Personalización de Facturas Electrónicas',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Plantilla y reporte PDF propios para la factura electrónica, en '
               'reemplazo del PDF estándar de Odoo.',
    'description': """
Personalización de Facturas Electrónicas
=========================================
Agrega un nuevo reporte PDF (`account_move_custom.report_custom_invoice`)
para las facturas y notas crédito de cliente, con una plantilla propia que
reemplaza al PDF estándar de Odoo en la vista previa e impresión, siempre que
el contacto o el diario no tengan ya configurada explícitamente otra
plantilla (`invoice_template_pdf_report_id`), en cuyo caso esa configuración
explícita tiene prioridad.

La plantilla (`report/account_move_report_templates.xml`) es un punto de
partida a terminar de diseñar.
""",
    'author': 'Porthos',
    'license': 'LGPL-3',
    'depends': [
        'account',
    ],
    'data': [
        'views/account_move_views.xml',
        'views/res_company_views.xml',
        'report/account_move_report_templates.xml',
        'report/account_move_reports.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
