# Copyright 2024 Moka (https://moka.cloud).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

_logger = logging.getLogger(__name__)

MODULE = 'l10n_fr_vat_on_margin'

# Records that used to be plain accounts and taxes owned by this module. They
# are now generated per company from templates, so these xmlids disappear from
# the module data. Odoo removes the records behind xmlids it no longer finds,
# which on a live database would delete taxes carried by posted invoices.
# Dropping the xmlid alone leaves the records in place, and the post-migration
# hands them back to the module by matching name and company.
LEGACY_XMLIDS = (
    'account_706500',
    'account_707500',
    'account_604500',
    'account_607500',
    'account_445750',
    'account_445665',
    'tax_margin_5_5_sale',
    'tax_margin_5_5_purchase',
    'tax_margin_10_sale',
    'tax_margin_10_purchase',
    'tax_margin_20_sale',
    'tax_margin_20_purchase',
)


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        "DELETE FROM ir_model_data WHERE module = %s AND name IN %s",
        (MODULE, LEGACY_XMLIDS),
    )
    _logger.info(
        "Detached %s legacy xmlids; their accounts and taxes are kept.",
        cr.rowcount,
    )
