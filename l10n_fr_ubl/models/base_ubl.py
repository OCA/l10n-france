# -*- coding: utf-8 -*-
# © 2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models, api
from lxml import etree


class BaseUbl(models.AbstractModel):
    _inherit = 'base.ubl'

    @api.model
    def _ubl_add_party_identification(
            self, commercial_partner, parent_node, ns, version='2.1'):
        res = super(BaseUbl, self)._ubl_add_party_identification(
            commercial_partner, parent_node, ns, version=version)
        if commercial_partner.siren and commercial_partner.nic:
            party_ident = etree.SubElement(
                parent_node, ns['cac'] + 'PartyIdentification')
            party_ident_id = etree.SubElement(
                party_ident, ns['cbc'] + 'ID', schemeName='1')
            party_ident_id.text = commercial_partner.siret
        return res
