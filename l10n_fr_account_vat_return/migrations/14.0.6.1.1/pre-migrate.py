# Copyright 2024 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


def migrate(cr, version):
    if not version:
        return

    cr.execute(
        "UPDATE account_move SET "
        "fiscal_position_fr_vat_type=account_fiscal_position.fr_vat_type "
        "FROM account_fiscal_position "
        "WHERE account_move.fiscal_position_id=account_fiscal_position.id "
        "AND account_move.fiscal_position_id is not null"
    )
