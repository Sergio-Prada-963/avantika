# -*- coding: utf-8 -*-
"""19.0.3.0.0: 'Ciudad Declaración ReteICA' pasa a ser 'Forzar ciudad ReteICA'.

Antes se llenaba automáticamente desde el contacto; ahora debe estar vacía por
defecto (la ciudad se calcula línea por línea). Se limpia en los documentos
abiertos para que no queden forzados por el valor viejo. Las facturas
publicadas no se tocan.
"""


def migrate(cr, version):
    if not version:
        return
    cr.execute("UPDATE account_move SET city_declaration_id = NULL WHERE state = 'draft'")
    cr.execute("""
        UPDATE sale_order SET city_declaration_id = NULL
         WHERE state != 'cancel' AND COALESCE(locked, FALSE) = FALSE
    """)
