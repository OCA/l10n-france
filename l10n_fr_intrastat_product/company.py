# -*- encoding: utf-8 -*-
##############################################################################
#
#    Report intrastat product module for OpenERP
#    Copyright (C) 2010-2011 Akretion (http://www.akretion.com). All Rights Reserved
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
from tools.translate import _

class res_company(osv.osv):
    _inherit = "res.company"
    _columns = {
        # In France, the customs_accreditation ("numéro d'habilitation")
        # is 4 char long. But the spec of the XML file says it can go up
        # to 8... because other EU countries may have identifiers up to 8 chars
        # As this module only implement DEB for France, we use size=4
        'customs_accreditation': fields.char('Customs accreditation identifier', size=4, help="Company identifier for Intrastat file export. Size : 4 characters."),
        'siret_complement' : fields.char('SIRET complement', size=5, help="5 last digits of the SIRET number of the company."),
        'export_obligation_level': fields.selection([('detailed', 'Detailed'), ('simplified', 'Simplified')], 'Obligation level for export', help='If your volume of export of products to EU countries is over 460 000 € per year, your obligation level for export for the DEB is "Detailed". If you are under this limit, your obligation level for export for the DEB is "Simplified".'),
        'default_intrastat_department': fields.char('Default departement code', size=2, help='If the Departement code is not set on the invoice line, OpenERP will use this value.'),
        'default_intrastat_transport': fields.selection([(1, 'Transport maritime'), \
            (2, 'Transport par chemin de fer'), \
            (3, 'Transport par route'), \
            (4, 'Transport par air'), \
            (5, 'Envois postaux'), \
            (7, 'Installations de transport fixes'), \
            (8, 'Transport par navigation intérieure'), \
            (9, 'Propulsion propre')], 'Type of transport', \
            help="If the 'Type of Transport' is not set on the invoice, OpenERP will use this value."),
    }

    def _5digits(self, cr, uid, ids):
        for siret_compl_to_check in self.read(cr, uid, ids, ['siret_complement']):
            if siret_compl_to_check['siret_complement']:
                if not siret_compl_to_check['siret_complement'].isdigit() or len(siret_compl_to_check['siret_complement']) != 5:
                    return False
        return True

    def real_department_check(self, dpt_list):
        for dpt in dpt_list:
            if not dpt:
                continue
            if dpt in ['2A', '2B']:
                continue
            if not dpt.isdigit():
                raise osv.except_osv(_('Error :'), _("The department code must be a number or have the value '2A' or '2B' for Corsica."))
            if int(dpt) < 1 or int(dpt) > 95:
                raise osv.except_osv(_('Error :'), _("The department code must be between 01 and 95 or have the value '2A' or '2B'."))
        return True

    def _check_default_intrastat_department(self, cr, uid, ids):
        dpt_list = []
        for dpt_to_check in self.read(cr, uid, ids, ['default_intrastat_department']):
            dpt_list.append(dpt_to_check['default_intrastat_department'])
        return self.real_department_check(dpt_list)

    _constraints = [
            (_5digits, "'SIRET complement' should have exactly 5 digits !", ['siret_complement']),
            (_check_default_intrastat_department, "Error msg is in raise", ['default_intrastat_department']),
            ]

res_company()

