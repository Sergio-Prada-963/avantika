# -*- coding: utf-8 -*-
{
    'name': 'Tasa de Cambio Manual por Documento',
    'version': '19.0.3.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Duplica el patrón nativo de TRM manual de Contabilidad en pagos, '
               'ventas y compras.',
    'description': """
Tasa de Cambio Manual por Documento
====================================
Odoo v19 ya permite fijar manualmente la tasa de cambio (TRM) de una factura
(campo `invoice_currency_rate`, con botón de "refrescar" a la tasa de la
tabla), sin alterar la tabla global de tasas de cambio (res.currency.rate).

Este módulo duplica ese mismo patrón (campo editable + botón de refrescar) en
los documentos que no lo tienen:

- **Pagos** (`account.payment`, y el asistente "Registrar Pago"): campo propio
  `manual_currency_rate` (independiente del `invoice_currency_rate` de
  facturas, para no depender de esa cadena de cómputo interna). Al fijarlo,
  se fuerza el `balance` (moneda de la compañía) de las líneas del pago vía el
  parámetro nativo `force_balance` de `_prepare_move_lines_per_type`, tanto al
  crear el pago como al editarlo después (se agregó a
  `_get_trigger_fields_to_synchronize` para que el formulario recalcule al
  guardar).
- **Cotizaciones/Pedidos de venta** (`sale.order`): tanto `currency_rate`
  como `currency_id` eran de solo lectura (la moneda solo se heredaba de la
  Lista de Precios). Se habilitan ambos para edición manual directa en el
  encabezado del pedido, con botón de refrescar para la tasa, y se propaga
  a la factura generada (`invoice_currency_rate`). El botón nativo
  "Actualizar Precios" (que normalmente solo aparece al cambiar la Lista de
  Precios) también se activa al cambiar la moneda manualmente.
- **Órdenes de compra** (`purchase.order`): `currency_id` ya era editable de
  forma nativa; se agrega el mismo tratamiento de `currency_rate` que en
  ventas.

En todos los casos la tasa manual solo es editable mientras el documento está
en borrador.

- **Facturas** (`account.move`): el campo nativo `invoice_currency_rate` se
  recalcula automáticamente cada vez que cambia la fecha de la factura,
  perdiendo cualquier tasa fijada a mano. Se preserva la tasa manual ante
  cambios de fecha (se sigue recalculando si se cambia la moneda, o al usar
  el botón nativo "Refrescar").
""",
    'author': 'Sergio Rodriguez',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'sale',
        'purchase',
    ],
    'data': [
        'views/account_move_views.xml',
        'views/account_payment_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'wizard/account_payment_register_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
