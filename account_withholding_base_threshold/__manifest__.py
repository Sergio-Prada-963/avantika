# -*- coding: utf-8 -*-
{
    'name': 'Bases Mínimas para Retenciones',
    'version': '19.0.3.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Aplica retenciones por posición fiscal, alcance de línea, ReteICA por municipio y base mínima en UVT.',
    'description': """
Bases Mínimas para Retenciones (UVT)
====================================
Agrega o quita automáticamente las retenciones de las líneas de facturas,
cotizaciones y órdenes de compra mientras el documento es editable.

Reglas por retención (account.tax), sin usar "Reemplaza":

- **Posición fiscal**: si la retención tiene posiciones, solo aplica cuando la
  posición del documento está entre ellas; sin posiciones aplica siempre
  (ej. autorretención).
- **Alcance**: Todos / Bienes / Servicios, solo ciertas categorías, excluir
  categorías y "Requiere IVA" (ej. ReteIVA 15% solo con IVA 19%).
- **Base UVT**: "Total de la Factura" suma solo las líneas a las que aplica la
  retención; "Líneas" evalúa cada una. La base se convierte a la moneda de la
  compañía. 0 UVT = aplica siempre.
- **ReteICA municipal**: la ciudad se toma línea por línea. Ventas: bienes →
  bodega de salida, servicios → dirección de entrega; el cliente debe tener
  "Me retiene ICA". Compras: bienes → bodega que recibe, servicios → "Ciudad
  del servicio"; el proveedor debe tener la tarifa en "Tarifas ReteICA".
  "Forzar ciudad ReteICA" en el encabezado manda sobre todas las líneas.

Los impuestos con "Reemplaza" (cambios de IVA) los maneja la posición fiscal
nativa y el módulo no los toca. Las notas crédito de una factura, los
documentos bloqueados, cancelados o ya facturados no se recalculan. Con Valor
UVT en 0 el módulo no hace nada.
""",
    'author': 'Sergio Rodriguez, Talaltos SAS',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'sale_stock',
        'purchase_stock',
        'base_address_extended',
    ],
    'data': [
        'views/account_tax_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
