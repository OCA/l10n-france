# -*- coding: utf-8 -*-
# Copyright 2015-2018 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, _


class BusinessDocumentImport(models.AbstractModel):
    _inherit = 'business.document.import'

    @api.model
    def _match_partner(
            self, partner_dict, chatter_msg, partner_type='supplier'):
        company_id = self._context.get('force_company') or\
            self.env.user.company_id.id
        domain = [
            '|', ('company_id', '=', False),
            ('company_id', '=', company_id)]
        if partner_type == 'supplier':
            domain += [('supplier', '=', True)]
        elif partner_type == 'customer':
            domain += [('customer', '=', True)]

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

    @api.model
    def _check_company(self, company_dict, chatter_msg):
        if not company_dict:
            company_dict = {}
        rco = self.env['res.company']
        if self._context.get('force_company'):
            company = rco.browse(self._context['force_company'])
        else:
            company = self.env.user.company_id
        if company_dict.get('siret'):
            parsed_company_siret = company_dict['siret'].replace(' ', '')
            if (
                    len(parsed_company_siret) == 14 and
                    parsed_company_siret.isdigit()):
                parsed_company_siren = parsed_company_siret[:9]
                if company.siren:
                    if company.siren != parsed_company_siren:
                        raise self.user_error_wrap(_(
                            "The SIREN of the customer written in the "
                            "business document (%s) doesn't match the SIREN "
                            "of the company '%s' (%s) in which you are "
                            "trying to import this document.") % (
                                parsed_company_siren, company.display_name,
                                company.siren))
                else:
                    chatter_msg.append(_(
                        "Missing SIRET on company '%s'")
                        % company.display_name)
        return super(BusinessDocumentImport, self)._check_company(
            company_dict, chatter_msg)
