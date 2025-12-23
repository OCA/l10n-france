# Copyright 2011-2022 Numérigraphe SARL.
# Copyright 2014-2022 Akretion France
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class ResCompany(models.Model):
    _inherit = "res.company"

    def _get_siret(self, raise_if_none=False):
        return self.partner_id._get_siret(raise_if_none=raise_if_none)

    def _get_siren(self, raise_if_none=False):
        return self.partner_id._get_siren(raise_if_none=raise_if_none)

    def _get_nic(self, raise_if_none=False):
        return self.partner_id._get_nic(raise_if_none=raise_if_none)
