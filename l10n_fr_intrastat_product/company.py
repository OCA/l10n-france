# -*- coding: utf-8 -*-
##############################################################################
#
#    L10n FR intrastat product module (DEB) for Odoo
#    Copyright (C) 2010-2015 Akretion (http://www.akretion.com)
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

from openerp import models, fields, api


class ResCompany(models.Model):
    _inherit = "res.company"

    # In France, the customs_accreditation ("numéro d'habilitation")
    # is 4 char long. But the spec of the XML file says it can go up
    # to 8... because other EU countries may have identifiers up to 8 chars
    # As this module only implement DEB for France, we use size=4
    fr_intrastat_accreditation = fields.Char(
        string='Customs accreditation identifier', size=4,
        help="Company identifier for Intrastat file export. "
        "Size : 4 characters.")

#    @api.onchange('import_obligation_level', 'export_obligation_level')
#    def obligation_level_on_change(self):
#        result = {'warning': {}}
#        if (self.export_obligation_level == 'detailed'
#                or self.import_obligation_level == 'detailed'):
#            result['warning']['title'] = _('Access Rights')
#            result['warning']['message'] = _(
#                "You should add users to the 'Detailed Intrastat Product' "
#                "group.")
#            result['warning']['message'] += '\n'
#            detailed_xmlid = 'l10n_fr_intrastat_product.'\
#                'group_detailed_intrastat_product'
#            if self.env['res.users'].has_group(detailed_xmlid):
#                result['warning']['message'] += _(
#                    "You are already in that group, but you may have to "
#                    "add other users to that group.")
#            else:
#                result['warning']['message'] += _(
#                    "You are not currently in that group.")
#        return result
