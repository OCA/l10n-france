# -*- encoding: utf-8 -*-
##############################################################################
#
#    Report intrastat product module for OpenERP
#    Copyright (C) 2010-2014 Akretion (http://www.akretion.com)
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


class res_company(orm.Model):
    _inherit = "res.company"

    _columns = {
        # In France, the customs_accreditation ("numéro d'habilitation")
        # is 4 char long. But the spec of the XML file says it can go up
        # to 8... because other EU countries may have identifiers up to 8 chars
        # As this module only implement DEB for France, we use size=4
        'customs_accreditation': fields.char(
            'Customs accreditation identifier', size=4,
            help="Company identifier for Intrastat file export. "
            "Size : 4 characters."),
        'siret_complement': fields.char(
            'SIRET complement', size=5,
            help="5 last digits of the SIRET number of the company."),
        'export_obligation_level': fields.selection(
            [('detailed', 'Detailed'), ('simplified', 'Simplified')],
            'Obligation level for export',
            help='For the DEB : if your volume of export of products to '
            'EU countries is over 460 000 € per year, your obligation '
            'level for export is "Detailed" ; if you are under this limit, '
            'your obligation level for export is "Simplified".'),
        'import_obligation_level': fields.selection(
            [('detailed', 'Detailed'), ('none', 'None')],
            'Obligation level for import',
            help="For the DEB : if your volume of import of products "
            "from EU countries is over 460 000 € per year, your obligation "
            "level for import is 'Detailed' ; if you are under this limit, "
            "you don't have to make a DEB for import and you should select "
            "'None'."),
        'default_intrastat_department': fields.char(
            'Default departement code', size=2,
            help='If the Departement code is not set on the invoice, '
            'OpenERP will use this value.'),
        'default_intrastat_transport': fields.selection([
            (1, 'Transport maritime'),
            (2, 'Transport par chemin de fer'),
            (3, 'Transport par route'),
            (4, 'Transport par air'),
            (5, 'Envois postaux'),
            (7, 'Installations de transport fixes'),
            (8, 'Transport par navigation intérieure'),
            (9, 'Propulsion propre'),
            ], 'Default type of transport',
            help="If the 'Type of Transport' is not set on the invoice, "
            "OpenERP will use this value."),
        'default_intrastat_type_out_invoice': fields.many2one(
            'report.intrastat.type',
            'Default intrastat type for customer invoice'),
        'default_intrastat_type_out_refund': fields.many2one(
            'report.intrastat.type',
            'Default intrastat type for customer refund'),
        'default_intrastat_type_in_invoice': fields.many2one(
            'report.intrastat.type',
            'Default intrastat type for supplier invoice'),
    }

    def _5digits(self, cr, uid, ids):
        for siret_compl_to_check in self.read(
                cr, uid, ids, ['siret_complement']):
            if siret_compl_to_check['siret_complement']:
                if (not siret_compl_to_check['siret_complement'].isdigit()
                        or len(siret_compl_to_check['siret_complement']) != 5):
                    return False
        return True

    def real_department_check(self, dpt_list):
        for dpt in dpt_list:
            if not dpt:
                continue
            if len(dpt) != 2:  # '1' is not accepted -> must be '01'
                raise orm.except_orm(
                    _('Error :'),
                    _("The department code must be 2 caracters long."))
            # 99 = Monaco, cf page 24 du BOD n°6883 du 06/01/2011
            if dpt in ['2A', '2B', '99']:
                continue
            if not dpt.isdigit():
                raise orm.except_orm(
                    _('Error :'),
                    _("The department code must be a number or have the "
                        "value '2A' or '2B' for Corsica."))
            if int(dpt) < 1 or int(dpt) > 95:
                raise orm.except_orm(
                    _('Error :'),
                    _("The department code must be between 01 and 95 or "
                        "have the value '2A' or '2B' for Corsica or '99' "
                        "for Monaco."))
        return True

    def _check_default_intrastat_department(self, cr, uid, ids):
        dpt_list = []
        for dpt_to_check in self.read(
                cr, uid, ids, ['default_intrastat_department']):
            dpt_list.append(dpt_to_check['default_intrastat_department'])
        return self.real_department_check(dpt_list)

    _constraints = [
        (
            _5digits,
            "The 'SIRET complement' should have exactly 5 digits.",
            ['siret_complement']
        ),
        (
            _check_default_intrastat_department,
            "error msg in raise",
            ['default_intrastat_department']
        ),
        ]

    def obligation_level_on_change(
            self, cr, uid, ids, export_obligation_level,
            import_obligation_level, context=None):
        result = {'warning': {}}
        if (export_obligation_level == 'detailed'
                or import_obligation_level == 'detailed'):
            result['warning']['title'] = _('Access Rights')
            result['warning']['message'] = _(
                "You should add users to the 'Detailed Intrastat Product' "
                "group.")
            result['warning']['message'] += '\n'
            detailed_xmlid = 'l10n_fr_intrastat_product.'\
                'group_detailed_intrastat_product'
            if self.pool['res.users'].has_group(cr, uid, detailed_xmlid):
                result['warning']['message'] += _(
                    "You are already in that group, but you may have to "
                    "add other users to that group.")
            else:
                result['warning']['message'] += _(
                    "You are not currently in that group.")
        return result
