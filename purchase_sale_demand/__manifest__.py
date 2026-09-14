# -*- coding: utf-8 -*-
{
    'name': 'Compra por Demanda desde Ventas',
    'version': '19.0.1.0.0',
    'category': 'Purchases/Purchases',
    'summary': 'Crea órdenes de compra por proveedor a partir de líneas de venta pendientes por comprar.',
    'description': """
Compra por Demanda desde Ventas
================================
La empresa no maneja inventario propio: cada venta confirmada dispara la
necesidad de comprar los productos a demanda. Este módulo agrega, dentro de
Compras, un listado de todas las líneas de venta confirmadas que aún tienen
cantidad pendiente por comprar, permitiendo seleccionar una o varias y crear
automáticamente una orden de compra en borrador por cada proveedor (tomado
de la línea de lista de precios de venta), vinculando cada línea de compra
generada con su línea de venta de origen. Al confirmar la compra, la
cantidad comprada se refleja en la línea de venta correspondiente.
""",
    'author': 'Sergio Rodriguez',
    'license': 'LGPL-3',
    'depends': [
        'sale',
        'sale_stock',
        'sale_margin',
        'purchase',
        'purchase_stock',
        'price_list_sales',
        'sale_order_custom',
        'mail',
        'mrp',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/sale_order_line_views.xml',
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
