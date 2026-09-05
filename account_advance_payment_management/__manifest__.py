{
    'name': 'Advance Payment Management',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Anticipos sin factura previa, control de saldo a favor y legalización automática',
    'description': """
Gestión Avanzada de Anticipos
=============================

Permite registrar cobros de clientes y pagos a proveedores como anticipo, sin
necesidad de una factura previa, contabilizándolos en una cuenta de pasivo
(anticipos de clientes) o de activo (anticipos a proveedores) configurable
por compañía en lugar de la cuenta por cobrar/pagar genérica.

Al emitir una factura o factura de proveedor al mismo tercero, el sistema
detecta el saldo a favor disponible en esas cuentas de anticipo y permite
aplicarlo con un clic, generando automáticamente el asiento de legalización
(reclasificación) que traslada el saldo de la cuenta de anticipo hacia la
cuenta por cobrar/pagar y concilia ambas partidas.

Este módulo es independiente: solo depende del módulo estándar `account` de
Odoo y no requiere ningún otro módulo custom instalado.
""",
    'author': 'Porthos',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_account_views.xml',
        'views/account_move_views.xml',
        'views/account_payment_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'wizard/account_advance_payment_apply_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
