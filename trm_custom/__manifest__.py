# -*- coding: utf-8 -*-
{
    'name': 'TRM Automática en Ventas, Compras y Facturas',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Campo TRM automático (moneda de la compañía por 1 unidad de la moneda del documento).',
    'description': """
TRM Automática
==============
Agrega un campo de solo lectura "TRM" en cotizaciones/pedidos de venta,
órdenes de compra y facturas (y notas de crédito/débito), que siempre
expresa cuántas unidades de la moneda de la compañía equivalen a 1 unidad
de la moneda del documento, según la tasa de cambio vigente en la fecha del
documento.

Ejemplo: si la moneda de la compañía es COP y el documento está en USD, y la
tasa de cambio vigente es tal que 1 USD = 3100 COP, el campo TRM muestra
3100 (independientemente de que la tabla interna de tasas de Odoo guarde la
relación en el sentido contrario). Si el documento ya está en la moneda de
la compañía, el campo siempre vale 1.

El campo se recalcula automáticamente al cambiar la moneda, la compañía, o
la fecha del documento (fecha de la orden en ventas/compras; fecha de la
factura, o de contabilización si la primera no está definida, en facturas).
""",
    'author': 'Sergio Rodriguez',
    'license': 'LGPL-3',
    'depends': [
        'sale',
        'purchase',
        'account',
    ],
    'data': [
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
