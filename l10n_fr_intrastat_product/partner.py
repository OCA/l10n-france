# -*- encoding: utf-8 -*-
##############################################################################
#
#    Report intrastat product module for OpenERP
#    Copyright (C) 2011 Akretion (http://www.akretion.com). All Rights Reserved
#    @author Alexis de Lattre <alexis.delattre@akretion.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv, fields

class res_partner(osv.osv):
    _inherit = "res.partner"
    _columns = {
        'intrastat_fiscal_representative' : fields.many2one('res.partner', string="EU fiscal representative", help="If the company is located outside the EU but you deliver the goods inside the UE, the company needs to have a fiscal representative with a VAT number inside the EU. In this scenario, the VAT number of the fiscal representative will be used for the Intrastat Product report."),
    }

    def _check_fiscal_representative(self, cr, uid, ids, context=None):
        '''The Fiscal rep. must be based in the same country as our company or in an intrastat country'''
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        my_company_country_id = user.company_id.partner_id.country and user.company_id.partner_id.country.id or False
        for partner in self.browse(cr, uid, ids, context=context):
            if partner.intrastat_fiscal_representative:
                if not partner.intrastat_fiscal_representative.country:
                    raise osv.except_osv(_('Error :'), _("The fiscal representative '%s' of partner '%s' must have a country") %(partner.intrastat_fiscal_representative.name, partner.name))
                if not partner.intrastat_fiscal_representative.country.intrastat and partner.intrastat_fiscal_representative.country.id <> my_company_country_id:
                    raise osv.except_osv(_('Error :'), _("The fiscal representative '%s' of partner '%s' must be based in an EU country") % (partner.intrastat_fiscal_representative.name, partner.name))
                if not partner.intrastat_fiscal_representative.vat:
                    raise osv.except_osv(_('Error :'), _("The fiscal representative '%s' of partner '%s' must have a VAT number") % (partner.intrastat_fiscal_representative.name, partner.name))

        return True

    _constraints = [
        (_check_fiscal_representative, "Error msg in raise", ['intrastat_fiscal_representative']),
    ]

res_partner()

