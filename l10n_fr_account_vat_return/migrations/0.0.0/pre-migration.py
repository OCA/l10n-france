# Copyright 2023 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

# According to odoo/modules/migration.py, a special folder named '0.0.0'
# can contain scripts that will be run on any version change


def migrate(cr, version):
    # When data/l10n.fr.account.vat.box.csv is updated,
    # a box can take the previous value of another box located
    # in a row after it in the CSV, so it hits the SQL constraint before
    # reaching/updating the other box in the CSV
    # Set I set to null the fields that are in a unique SQL constraint
    cr.execute(
        "UPDATE l10n_fr_account_vat_box SET sequence=null, nref_code=null, "
        "print_x=null, print_y=null, print_page=null, code=null"
    )
