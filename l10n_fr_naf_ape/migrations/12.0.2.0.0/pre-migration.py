# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    cr.execute(
        """
        UPDATE ir_model_data
        SET name=concat('old_', name)
        WHERE name LIKE 'naf_%'
        """
    )
    cr.execute(
        """
        ALTER TABLE res_partner
        ADD COLUMN IF NOT EXISTS ape_id_tmp INTEGER
        """
    )
    cr.execute(
        """
        UPDATE res_partner
        SET ape_id_tmp = ape_id
        """
    )
