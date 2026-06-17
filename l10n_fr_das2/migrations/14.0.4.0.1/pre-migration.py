# Copyright 2026 Altixia (https://www.altixia.com)
# @author: Claude Perrin <claude@altixia.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    if not version:
        return
    # The 'fr_das2_partner_declare_threshold' setting field was removed in
    # v14.0.4.0.0 (the declaration threshold is now provided by the pyfrdas2
    # lib). Its res.config.settings view 'view_account_config_settings' was
    # removed from the module too, but the stale DB record keeps referencing
    # the dropped field. During an upgrade, as soon as another module
    # re-renders res.config.settings, view validation raises
    # "Field 'fr_das2_partner_declare_threshold' does not exist in model
    # 'res.config.settings'" and the registry fails to load. Odoo would
    # eventually drop the orphan view in _process_end, but the crash happens
    # before that. Drop the obsolete view here, before the views are reloaded.
    cr.execute(
        """
        DELETE FROM ir_ui_view
        WHERE id IN (
            SELECT res_id
            FROM ir_model_data
            WHERE module = 'l10n_fr_das2'
              AND model = 'ir.ui.view'
              AND name = 'view_account_config_settings'
        )
        """
    )
