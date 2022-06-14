# Copyright 2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from openupgradelib import openupgrade

column_renames = {
    'res_partner': [
        ('supplier_vat_on_payment', None),
    ],
    'account_move': [
        ('in_vat_on_payment', None),
    ],
    }


@openupgrade.migrate()
def migrate(env, version):
    if not version:
        return
    openupgrade.rename_columns(env.cr, column_renames)
