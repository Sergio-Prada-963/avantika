# -*- coding: utf-8 -*-
{
    'name': 'Contabilidad Dual NIIF / Fiscal (Core)',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Motor de contabilidad multi-libro: replica automáticamente cada asiento contable '
               'en un libro contable secundario (Fiscal) al contabilizar el asiento primario (NIIF).',
    'description': """
Contabilidad Dual NIIF / Fiscal - Núcleo
=========================================
Implementa una arquitectura de Contabilidad Multi-Libro (Multi-Book Accounting)
que permite registrar cada transacción contable bajo dos normativas en paralelo
(ej. NIIF/IFRS como libro primario y Fiscal/Local como libro secundario).

- Define "Libros Contables" (account.book): agrupan diarios por método
  (Primario / Secundario).
- Al contabilizar un asiento del libro primario, se genera automáticamente
  un asiento espejo en el diario del libro secundario, mapeando cada cuenta
  contable a su cuenta equivalente en el plan de cuentas secundario
  (account.account.secondary_account_id).
- El asiento espejo queda enlazado al asiento origen (origin_move_id) y
  marcado como generado automáticamente (is_dual_generated), evitando así
  ciclos de replicación.

Este módulo es la base (core) sobre la que se apoya el módulo de gestión
dual de activos fijos (account_dual_asset_management).
""",
    'author': 'Sergio Rodriguez',
    'license': 'LGPL-3',
    'depends': [
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/account_book_views.xml',
        'views/account_account_views.xml',
        'views/account_move_views.xml',
        'data/account_book_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
