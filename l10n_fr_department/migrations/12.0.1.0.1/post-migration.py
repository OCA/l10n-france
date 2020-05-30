# Copyright 2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    if not version:
        return

    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        fr_countries = env['res.country'].search(
            [('code', 'in', ('FR', 'GP', 'MQ', 'GF', 'RE', 'YT'))])
        partners = env['res.partner'].with_context(active_test=False).search(
            [
                ('country_id', 'in', fr_countries.ids),
                ('zip', '=like', '0%'),
            ])
        partners._compute_department()
