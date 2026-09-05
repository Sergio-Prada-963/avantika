# -*- coding: utf-8 -*-
{
    'name': 'Deterioro de Cartera (NIIF 9)',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Cálculo y contabilización del deterioro de cartera por matriz de rangos de mora.',
    'description': """
Deterioro de Cartera (NIIF 9)
==============================
Automatiza la estimación y contabilización de la pérdida esperada de cuentas
por cobrar (cartera vencida), aplicando una matriz de riesgo por antigüedad
de mora (NIIF 9 / provisión fiscal), y genera el asiento de ajuste neto entre
la provisión requerida y la ya registrada en el mayor.

Flujo:

1. Analizar cartera: se leen los saldos abiertos de las facturas de cliente
   (`account.move.line` con cuenta de tipo `asset_receivable`) y sus días de
   mora respecto a la fecha de vencimiento.
2. Aplicar matriz: cada saldo se clasifica en un rango de mora configurable
   (matriz de riesgo) y se le asigna el porcentaje de pérdida esperada.
3. Calcular ajuste: se compara la provisión requerida por tercero contra la
   ya registrada en la cuenta de provisión (leída directamente del mayor,
   no de un campo propio) para obtener el ajuste neto.
4. Asiento contable: se contabiliza el ajuste neto por tercero contra la
   cuenta de gasto y la cuenta de provisión (contra-activo).

La configuración (cuentas, diario, periodicidad y rangos de mora) vive
directamente en la compañía y se edita desde Contabilidad → Ajustes: no
existe un modelo de "matriz" aparte, solo una configuración por compañía.

Un cron diario revisa la "Periodicidad de Cálculo Automático" configurada
(mensual, bimensual, trimestral, semestral o anual) y crea, en borrador, un
nuevo cálculo de deterioro cuando corresponde según esa periodicidad.

Al calcular, solo se consideran facturas efectivamente vencidas a la fecha
de corte (días de mora > 0) y que además caigan dentro de alguno de los
rangos de mora configurados.
""",
    'author': 'Sergio Rodriguez',
    'license': 'LGPL-3',
    'depends': [
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'views/account_receivable_impairment_calculation_views.xml',
        'views/account_move_views.xml',
        'views/account_account_views.xml',
        'views/account_receivable_impairment_menus.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
