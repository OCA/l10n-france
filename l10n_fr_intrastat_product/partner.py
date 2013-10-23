# -*- encoding: utf-8 -*-
##############################################################################
#
#    Report intrastat product module for OpenERP
#    Copyright (C) 2011-2013 Akretion (http://www.akretion.com)
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

from openerp.osv import orm, fields
from openerp.tools.translate import _


class res_partner(orm.Model):
    _inherit = "res.partner"
    _columns = {
        'intrastat_fiscal_representative': fields.many2one('res.partner', string="EU fiscal representative", help="If this partner is located outside the EU but you deliver the goods inside the UE, the partner needs to have a fiscal representative with a VAT number inside the EU. In this scenario, the VAT number of the fiscal representative will be used for the Intrastat Product report (DEB)."),
    }

    # Copy field 'intrastat_fiscal_representative' from company partners to their contacts
    def _commercial_fields(self, cr, uid, context=None):
        res = super(res_partner, self)._commercial_fields(cr, uid, context=context)
        res.append('intrastat_fiscal_representative')
        return res

    def _check_fiscal_representative(self, cr, uid, ids):
        '''The Fiscal rep. must be based in the same country as our company or in an intrastat country'''
        user = self.pool.get('res.users').browse(cr, uid, uid)
        my_company_country_id = user.company_id.partner_id.country and user.company_id.partner_id.country.id or False
        for partner in self.browse(cr, uid, ids):
            if partner.intrastat_fiscal_representative:
                if not partner.intrastat_fiscal_representative.country:
                    raise orm.except_orm(_('Error :'), _("The fiscal representative '%s' of partner '%s' must have a country.") % (partner.intrastat_fiscal_representative.name, partner.name))
                if not partner.intrastat_fiscal_representative.country.intrastat and partner.intrastat_fiscal_representative.country.id != my_company_country_id:
                    raise orm.except_orm(_('Error :'), _("The fiscal representative '%s' of partner '%s' must be based in an EU country.") % (partner.intrastat_fiscal_representative.name, partner.name))
                if not partner.intrastat_fiscal_representative.vat:
                    raise orm.except_orm(_('Error :'), _("The fiscal representative '%s' of partner '%s' must have a VAT number.") % (partner.intrastat_fiscal_representative.name, partner.name))

        return True

    _constraints = [
        (_check_fiscal_representative, "Error msg in raise", ['intrastat_fiscal_representative']),
    ]
