# Copyright 2025 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    # Force recompute of field 'fr_vat_autoliquidation'
    all_taxes = env["account.tax"].with_context(active_test=False).search([])
    all_taxes._compute_fr_vat_autoliquidation()
