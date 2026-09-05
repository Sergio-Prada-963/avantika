# -*- coding: utf-8 -*-
{
    'name': 'Bases Mínimas para Retenciones',
    'version': '19.0.2.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Aplica o exime automáticamente una retención según el valor en UVT de la base gravable de la factura.',
    'description': """
Bases Mínimas para Retenciones (UVT)
======================================
Aplica o retira automáticamente una retención (account.tax con monto
negativo) de las líneas de una factura, cotización u orden de compra, en
tiempo real, según si la base gravable alcanza un mínimo expresado en UVT.

Configuración en cada retención:

- **Aplica Base UVT**: activa el control automático para esa retención.
- **Base para Calcular**: "Total de la Factura" evalúa el documento completo;
  "Líneas de la Factura" evalúa cada línea de forma independiente.
- **Cantidad UVT**: número de UVT que debe alcanzar esa base.
- El **Tipo de Impuesto** (Ventas/Compras) determina en cuál documento
  aplica: Ventas → facturas de cliente y cotizaciones; Compras → facturas
  de proveedor y órdenes de compra.

Configuración en Contabilidad → Ajustes:

- **Valor UVT**: valor en COP de la UVT vigente. El mínimo efectivo de cada
  retención es "Cantidad UVT" × "Valor UVT".

Comportamiento: en cada edición de las líneas (factura, cotización u orden
de compra, mientras el documento es editable), se recalcula la base de cada
retención configurada y se agrega o se quita de las líneas correspondientes
según si se alcanza o no el mínimo — sin esperar a confirmar el documento.
El mismo cálculo corre también al crear el documento desde cualquier otro
flujo, y como respaldo final justo antes de contabilizar/confirmar.

ReteICA Territorializada por Municipio
======================================
Una retención (account.tax) puede marcarse como "Es ReteICA Municipal" y
asociarse a una "Ciudad / Municipio"; su base mínima se configura igual que
cualquier otra retención, con "Aplica Base UVT". El contacto tiene un campo
"Ciudad de Declaración ReteICA"; al crear o editar una cotización o factura
de cliente, ese municipio se propone en el encabezado (sobreescribible), y
el sistema solo aplica automáticamente la retención de ReteICA cuya ciudad
coincida con la declarada — evaluando la misma base mínima en UVT que el
resto de retenciones.
""",
    'author': 'Sergio Rodriguez',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'sale',
        'purchase',
        'base_address_extended',
    ],
    'data': [
        'views/account_tax_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
