# Copyright 2025 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def fr_vat_setup(env):
    env["res.company"]._fr_vat_init_adjustment_accounts_all_companies()
