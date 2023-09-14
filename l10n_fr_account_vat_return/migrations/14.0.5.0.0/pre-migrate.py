# Copyright 2023 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    if not version:
        return
    openupgrade.logged_query(
        env.cr,
        "UPDATE l10n_fr_account_vat_return_line_log "
        "SET compute_type='base_from_balance_ratio' "
        "WHERE compute_type ='computed_base'",
    )
    openupgrade.logged_query(
        env.cr,
        "UPDATE l10n_fr_account_vat_return_line_log "
        "SET compute_type='base_from_balance' "
        "FROM l10n_fr_account_vat_return_line "
        "WHERE l10n_fr_account_vat_return_line.id="
        "l10n_fr_account_vat_return_line_log.parent_id "
        "AND l10n_fr_account_vat_return_line_log.compute_type='balance' "
        "AND l10n_fr_account_vat_return_line.box_box_type ilike 'taxed_op_%'",
    )
    openupgrade.logged_query(
        env.cr,
        "UPDATE l10n_fr_account_vat_return_line_log "
        "SET compute_type='base_from_unpaid_vat_on_payment' "
        "FROM l10n_fr_account_vat_return_line "
        "WHERE l10n_fr_account_vat_return_line.id="
        "l10n_fr_account_vat_return_line_log.parent_id "
        "AND l10n_fr_account_vat_return_line_log.compute_type='unpaid_vat_on_payment' "
        "AND l10n_fr_account_vat_return_line.box_box_type ilike 'taxed_op_%'",
    )
