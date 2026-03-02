from odoo import _
from odoo.exceptions import UserError


def pre_init_check_hook(env):
    module_siret = env["ir.module.module"].search(
        [
            ("name", "=", "l10n_fr_siret_lookup"),
            ("state", "in", ["installed", "to install", "to upgrade"]),
        ]
    )

    if module_siret:
        raise UserError(
            _(
                "Installation failed: The 'SIRET Lookup' (l10n_fr_siret_lookup) module "
                "is already present. Please uninstall it before installing INPI Lookup."
            )
        )
