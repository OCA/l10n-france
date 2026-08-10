# Copyright 2024 Moka (https://moka.cloud).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.addons.l10n_fr_vat_on_margin.hooks import post_init_hook


def migrate(cr, version):
    """Run the install hook on upgrade too.

    post_init_hook only fires on install, so an existing database would keep
    the single-company layout. The hook adopts the accounts and taxes the
    pre-migration detached instead of creating duplicates, and fills in the
    companies that had none.
    """
    if not version:
        return
    post_init_hook(cr, None)
