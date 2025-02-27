from . import models
from odoo.addons.account.models.chart_template import preserve_existing_tags_on_taxes


def _l10n_fr_post_init_hook(env):
    preserve_existing_tags_on_taxes(env, "l10n_fr_account_oca")
