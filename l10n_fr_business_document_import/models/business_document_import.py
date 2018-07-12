# -*- coding: utf-8 -*-
# © 2015-2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


class BusinessDocumentImport(models.AbstractModel):
    _inherit = 'business.document.import'

    @api.model
    def _match_partner(
            self, partner_dict, chatter_msg, partner_type='supplier'):
        if partner_type == 'supplier':
            domain = [('supplier', '=', True)]
        elif partner_type == 'customer':
            domain = [('customer', '=', True)]
        else:
            domain = []

        if partner_dict.get('siret'):
            siret = partner_dict['siret'].replace(' ', '')
            if len(siret) == 14 and siret.isdigit():
                partners = self.env['res.partner'].search(
                    domain + [
                        ('parent_id', '=', False),
                        ('siret', '=', siret),
                        ])
                if partners:
                    return partners[0]
                # fallback on siren search
                elif not partner_dict.get('siren'):
                    partner_dict['siren'] = siret[:9]
        if partner_dict.get('siren'):
            siren = partner_dict['siren'].replace(' ', '')
            if len(siren) == 9 and siren.isdigit():
                partners = self.env['res.partner'].search(
                    domain + [
                        ('parent_id', '=', False),
                        ('siren', '=', siren),
                        ])
                if partners:
                    return partners[0]
        return super(BusinessDocumentImport, self)._match_partner(
            partner_dict, chatter_msg, partner_type=partner_type)
