# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def migrate(cr, registry):
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        cr.execute(
            """
            SELECT id, ape_id_tmp
            FROM res_partner
            WHERE ape_id_tmp IS NOT NULL
            """
        )
        rows = cr.fetchall()
        for partner_id, ape_id_tmp in rows:
            partner = env["res.partner"].browse(partner_id)
            category = env["res.partner.category"].browse(ape_id_tmp)
            partner.ape_id = env.ref(
                category.get_external_id().get(category.id).replace('old_', '')
            )
    cr.execute(
        """
        DELETE FROM res_partner_category
        WHERE id IN (
            SELECT res_id
            FROM ir_model_data
            WHERE name like 'old_naf_%'
        )
        """
    )
