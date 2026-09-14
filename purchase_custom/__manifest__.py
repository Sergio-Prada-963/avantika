# -*- coding: utf-8 -*-
{
    'name': 'Personalizaciones de Órdenes de Compra',
    'version': '19.0.1.0.0',
    'category': 'Purchases/Purchases',
    'summary': 'Compra AIU, aprobación de compras por correo y wizards de cambiar producto/bodega.',
    'description': """
Personalizaciones de Órdenes de Compra
=======================================
Agrupa las personalizaciones propias de la orden de compra:

- Compra AIU (Administración, Imprevistos, Utilidades): equivalente a la
  "Cotización AIU" que ya existe en ventas. Al activar el check "Compra
  AIU" se agregan automáticamente una sección "Costos indirectos" y 3
  líneas (Administración, Imprevistos, Utilidades) cuyo precio se calcula
  como un porcentaje configurable sobre la suma de las demás líneas de la
  compra. Los 3 productos a usar se configuran en Compras > Configuración
  > Ajustes.

- Flujo de aprobación de compras por correo: el botón nativo de
  confirmar/aprobar se oculta en borrador, enviada y por aprobar,
  reemplazado por un botón "Enviar Aprobación" que arma una previsualización
  del margen de la orden (y de sus kits, si aplica) y abre el compositor de
  correo estándar de Odoo, listo para enviar al "Usuario que Aprueba
  Compras" configurado en Ajustes > Compras. Al enviar el correo, la orden
  pasa a "Por Aprobar"; el correo incluye un botón "Aprobar" (enlace de un
  clic, sin necesidad de iniciar sesión) que confirma la orden directamente.
  Los usuarios con el permiso "Confirmar Compras sin Aprobación" activo en
  sus preferencias ven en su lugar un botón "Confirmar" que las confirma
  directamente, sin pasar por este flujo.

- Wizard "Cambiar Producto": cambia el producto de una línea de compra y
  propaga el cambio a la línea de venta de origen (si existe) y a sus
  movimientos de entrega.

- Wizard "Cambiar Bodega": cambia la bodega de destino de la compra y
  propaga el cambio a sus recepciones (pickings/movimientos) pendientes.
""",
    'author': 'Sergio Rodriguez',
    'license': 'LGPL-3',
    'depends': [
        'purchase',
        'purchase_stock',
        'sale',
        'sale_stock',
        'sale_order_custom',
        'price_list_sales',
        'purchase_sale_demand',
        'portal',
        'mail',
        'mrp',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/purchase_order_approval_server_action.xml',
        'wizard/purchase_order_change_product_wizard_views.xml',
        'wizard/purchase_order_change_warehouse_wizard_views.xml',
        'views/purchase_order_views.xml',
        'views/purchase_order_approval_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'views/portal_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
