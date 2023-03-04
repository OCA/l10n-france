# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).


from odoo import api, SUPERUSER_ID
from odoo.addons.account.models.chart_template import preserve_existing_tags_on_taxes


def _l10n_fr_post_init_hook(cr, registry):
    preserve_existing_tags_on_taxes(cr, registry, "l10n_fr_oca")
