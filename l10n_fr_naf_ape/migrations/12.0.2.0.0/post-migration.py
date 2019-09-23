# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api
from collections import defaultdict


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
        ape_dict = defaultdict(int)
        ape_model = env['res.partner.nace']
        for partner_id, ape_id_tmp in rows:
            partner = env["res.partner"].browse(partner_id)
            category = env["res.partner.category"].browse(ape_id_tmp)
            xml_id = (
                category.get_external_id().get(category.id).replace('old_', '')
            )
            if ape_id_tmp not in ape_dict:
                if 'naf' in xml_id:
                    ape_dict[ape_id_tmp] = env.ref(xml_id)
                else:
                    ape_dict[ape_id_tmp] = ape_model.create(
                        {'name': category.name}
                    )
            partner.ape_id = ape_dict[ape_id_tmp]
