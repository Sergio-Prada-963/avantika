# -*- coding: utf-8 -*-
{
    'name': 'Programación de Pagos a Proveedores',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Programa pagos concurrentes y anticipos a proveedores, agrupados por tercero.',
    'description': """
Programación de Pagos a Proveedores
====================================
Permite armar programaciones de pago que agrupan varias facturas de
proveedor (potencialmente de distintos terceros) y, al confirmarlas, generan
un único account.payment por tercero, con una línea de asiento por cada
factura incluida. Si el monto a pagar de un tercero supera el total
adeudado, el excedente se registra como anticipo en la cuenta de anticipos
a proveedor configurada (del contacto o, en su defecto, de la compañía, vía
el módulo account_advance_payment_management).

Incluye una acción planificada configurable en Ajustes para generar estas
programaciones automáticamente, tomando las facturas próximas a vencer.
""",
    'author': 'Sergio Rodriguez',
    'license': 'LGPL-3',
    'depends': [
        'mail',
        'account',
        'account_advance_payment_management',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'views/account_payment_schedule_views.xml',
        'views/account_payment_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/account_payment_schedule_add_lines_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
