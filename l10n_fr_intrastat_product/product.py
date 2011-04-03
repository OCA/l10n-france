# -*- encoding: utf-8 -*-
##############################################################################
#
#    Report intrastat product module for OpenERP
#    Copyright (C) 2004-2009 Tiny SPRL (http://tiny.be). All Rights Reserved
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

class report_intrastat_code(osv.osv):
    _name = "report.intrastat.code"
    _description = "Intrastat code"
    _order = "name"
    _columns = {
        'name': fields.char('Intrastat code', size=16, required=True, help="Full lenght H.S. code"),
        'description': fields.char('Description', size=128, help='Short text description of the H.S. category'),
        'code8': fields.char('Intrastat code 8 digits', size=8, required=True, help="8 digits long H.S. code. Used for the DEB in France (called 'Nomenclature combinée NC8')"),
        'intrastat_uom_id': fields.many2one('product.uom', 'UoM for intrastat product report', help="Select the unit of measure if one is required for this particular intrastat code. If no particular unit of measure is required, leave empty and the Intrastat product report will contain the weight."),
    }

    def _8digits(self, cr, uid, ids):
        for code8_to_check in self.read(cr, uid, ids, ['code8']):
            if code8_to_check['code8']:
                if not code8_to_check['code8'].isdigit() or len(code8_to_check['code8']) != 8:
                    return False
        return True

    def _digits(self, cr, uid, ids):
        for code_to_check in self.read(cr, uid, ids, ['name']):
            if code_to_check['name']:
                if not code_to_check['name'].isdigit():
                    return False
        return True

    _constraints = [
        (_8digits, "'Intrastat code 8 digits' should have exactly 8 digits !", ['code8']),
        (_digits, "'Intrastat code' should only contain digits.", ['name']),
         ]

report_intrastat_code()


class product_uom(osv.osv):
    _inherit = "product.uom"
    _columns = {
        'intrastat_label': fields.char('Intrastat label', size=12, help="Label used in the XML file export of the Intrastat product report for this unit of measure."),
        }

product_uom()


class product_template(osv.osv):
    _inherit = "product.template"
    _columns = {
        'intrastat_id': fields.many2one('report.intrastat.code', 'Intrastat code', help="Code from the Harmonised System. Nomenclature is available from the World Customs Organisation, see http://www.wcoomd.org/. Some countries have made their own extensions to this nomenclature."),
        'country_id' : fields.many2one('res.country', 'Country of origin', help="Country of origin of the product i.e. product 'made in ...'."),
    }

product_template()

