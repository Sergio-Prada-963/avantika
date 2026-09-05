# -*- coding: utf-8 -*-
{
    'name': 'Retención Dinámica en Pagos Multifactura',
    'version': '19.0.2.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Agrega retenciones por factura directamente desde el asistente nativo de registro de pago.',
    'description': """
Retención Dinámica en Pagos Multifactura
==========================================
Integra la aplicación de retenciones (ReteFuente, ReteICA, ReteIVA u otras)
directamente en el asistente NATIVO de Odoo para registrar pagos ("Pagar"),
sin agregar un botón ni un asistente aparte.

Al abrir el asistente de pago desde una o varias facturas de un mismo
tercero, se agrega una tabla con el detalle de cada factura incluida:
número, tercero, fecha de vencimiento, valor sin impuesto, total, cantidad
por pagar, impuestos (editable) e importe a abonar.

- Se pueden agregar más facturas del MISMO tercero a la tabla (no se crean
  facturas nuevas, se seleccionan de las ya existentes y contabilizadas).
- No se permite mezclar facturas de distintos terceros en el mismo pago.
- La columna de impuestos es editable, pero la factura NUNCA se modifica:
  un impuesto agregado en el wizard que no estaba ya en la factura se
  contabiliza como una línea aparte en el asiento del pago (retención al
  momento del pago), cruzada contra lo que de otro modo iría a la cuenta
  bancaria/caja.
- Con "Agrupar Pagos" activo, se puede definir un "Importe" distinto por
  factura (nunca por encima de su cantidad por pagar) para abonar
  parcialmente una factura específica dentro de un pago agrupado; el
  impuesto agregado a esa factura se prorratea según el porcentaje pagado.
  Sin agrupar, el importe siempre es el total de cada factura.
- Con "Agrupar Pagos" activo, el asiento del pago mantiene una línea de
  contrapartida por cada factura (no las combina en una sola línea por el
  total), más una línea por cada impuesto agregado.

Limitaciones conocidas:
- No cubre facturas en moneda extranjera con tasas de cambio distintas
  entre la fecha de la factura y la fecha de pago.
- Las líneas de retención agregadas no generan automáticamente las
  etiquetas/casillas del reporte de impuestos (solo se prioriza que la
  cuenta y el monto contable queden correctos); si se necesita reporte
  fiscal completo de estas retenciones, requiere una extensión futura.
- Si el pago agrupado no queda en modo "editable" internamente (caso raro:
  cuenta bancaria del tercero no validada, u otras condiciones que Odoo usa
  para decidirlo), el reparto de la contrapartida por factura no aplica y
  se usa el comportamiento nativo (una sola línea combinada).
""",
    'author': 'Sergio Rodriguez',
    'license': 'LGPL-3',
    'depends': [
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizards/account_payment_register_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
