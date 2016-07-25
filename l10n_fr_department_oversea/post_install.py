# -*- coding: utf-8 -*-
# © 2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import SUPERUSER_ID


def set_oversea_department_on_partner(cr, pool):
    """This post_install script is required because, when the module
    is installed, Odoo creates the column in the DB and compute the field
    and THEN it loads the file data/res_country_department_data.yml...
    So, when it computes the field on module installation, the
    departments are not available in the DB, so the department_id field
    on res.partner stays null. This post_install script fixes this."""
    rpo = pool['res.partner']
    fr_country_ids = pool['res.country'].search(
        cr, SUPERUSER_ID,
        [('code', 'in', ('FR', 'GP', 'MQ', 'GF', 'RE', 'YT'))])
    partner_ids = rpo.search(
        cr, SUPERUSER_ID,
        [
            '|', ('active', '=', False), ('active', '=', True),
            ('country_id', 'in', fr_country_ids),
            ('department_id', '=', False),
        ])
    partners = rpo.browse(cr, SUPERUSER_ID, partner_ids)
    partners._compute_department()
    return
