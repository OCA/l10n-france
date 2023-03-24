# -*- coding: utf-8 -*-
# © 2015-2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models, api


class BusinessDocumentImport(models.AbstractModel):
    _inherit = 'business.document.import'

    @api.model
    def _match_partner(
            self, partner_dict, chatter_msg, partner_type='supplier'):
        if partner_dict.get('siren'):
            siren = partner_dict['siren'].replace(' ', '')
            if len(siren) == 9:
                if partner_type == 'supplier':
                    domain = [('supplier', '=', True)]
                elif partner_type == 'customer':
                    domain = [('customer', '=', True)]
                else:
                    domain = []
                partners = self.env['res.partner'].search(
                    domain + [
                        ('parent_id', '=', False),
                        ('siren', '=', siren),
                        ])
                if partners:
                    return partners[0]
        return super(BusinessDocumentImport, self)._match_partner(
            partner_dict, chatter_msg, partner_type=partner_type)
