# Copyright 2023 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

# According to odoo/modules/migration.py, a special folder named '0.0.0'
# can contain scripts that will be run on any version change

from openupgradelib import openupgrade


def migrate(cr, version):
    # Remove the unicity constraint on several box fields,
    # because, when data/l10n.fr.account.vat.box.csv is updated,
    # a box can take the previous value of another box located
    # in a row after it in the CSV, so it hits the SQL constraint before
    # reaching/updating the other box in the CSV
    box_fields = ["sequence", "form_code", "code", "nref_code", "print_x"]
    for box_field in box_fields:
        openupgrade.lift_constraints(cr, "l10n_fr_account_vat_box", box_field)
