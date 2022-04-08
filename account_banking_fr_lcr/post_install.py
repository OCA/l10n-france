# Copyright 2016-2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def lcr_set_unece(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    lcr = env.ref("account_banking_fr_lcr.fr_lcr")
    if lcr:
        # This module doesn't depend on account_payment_unece
        # so we test the attribute 'unece_id' on the payment method
        # to know if the module is installed or not
        if hasattr(lcr, "unece_id"):
            lcr_unece = env.ref(
                "account_payment_unece.payment_means_24", raise_if_not_found=False
            )
            if lcr_unece:
                lcr.write({"unece_id": lcr_unece.id})
    return
