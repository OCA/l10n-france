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
        'name': fields.char('H.S. code', size=16, required=True, help="Full lenght H.S. code"),
        'description': fields.char('Description', size=255, help='Short text description of the H.S. category'),
        'intrastat_code': fields.char('Intrastat code for DEB', size=9, required=True, help="H.S. code used for the DEB in France. Must be part of the 'Nomenclature combinée' (NC) with 8 digits with sometimes a 9th digit for the 'Nomenclature Générale des Produits' (NGP)."),
        'intrastat_uom_id': fields.many2one('product.uom', 'UoM for intrastat product report', help="Select the unit of measure if one is required for this particular intrastat code (other than the weight in Kg). If no particular unit of measure is required, leave empty."),
    }

    def _intrastat_code(self, cr, uid, ids):
        for intrastat_code_to_check in self.read(cr, uid, ids, ['intrastat_code']):
            if intrastat_code_to_check['intrastat_code']:
                if not intrastat_code_to_check['intrastat_code'].isdigit() or len(intrastat_code_to_check['intrastat_code']) not in (8, 9):
                    return False
        return True

    def _hs_code(self, cr, uid, ids):
        for code_to_check in self.read(cr, uid, ids, ['name']):
            if code_to_check['name']:
                if not code_to_check['name'].isdigit():
                    return False
        return True

    _constraints = [
        (_intrastat_code, "The 'Intrastat code for DEB' should have exactly 8 or 9 digits.", ['intrastat_code']),
        (_hs_code, "'Intrastat code' should only contain digits.", ['name']),
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
        'country_id' : fields.many2one('res.country', 'Country of origin',
            help="Country of origin of the product i.e. product 'made in ____'. If you have different countries of origin depending on the supplier from which you purchased the product, leave this field empty and use the equivalent field on the 'product supplier info' form."),
        # This field should be called origin_country_id, but it's named country_id to keep "compatibility with OpenERP users that used the "report_intrastat" module

    }

product_template()


class product_category(osv.osv):
    _inherit = "product.category"
    _columns = {
        'intrastat_id': fields.many2one('report.intrastat.code', 'Intrastat code', help="Code from the Harmonised System. If this code is not set on the product itself, it will be read here, on the related product category."),
    }

product_category()


class product_supplierinfo(osv.osv):
    _inherit = "product.supplierinfo"
    _columns = {
        'origin_country_id' : fields.many2one('res.country', 'Country of origin',
            help="Country of origin of the product (i.e. product 'made in ____') when purchased from this supplier. This field is used only when the equivalent field on the product form is empty."),
        }

    def _same_supplier_same_origin(self, cr, uid, ids):
        """Products from the same supplier should have the same origin"""
        for supplierinfo in self.browse(cr, uid, ids):
            country_origin_id = supplierinfo.origin_country_id.id
            # Search for same supplier and same product
            same_product_same_supplier_ids = self.search(cr, uid, [('product_id', '=', supplierinfo.product_id.id), ('name', '=', supplierinfo.name.id)])
            # 'name' on product_supplierinfo is a many2one to res.partner
            for supplieri in self.browse(cr, uid, same_product_same_supplier_ids):
                if country_origin_id != supplieri.origin_country_id.id:
                    raise osv.except_osv(_('Error !'), _("For a particular product, all supplier info entries with the same supplier should have the same country of origin. But, for product '%s' with supplier '%s', there is one entry with country of origin '%s' and another entry with country of origin '%s'.") % (supplieri.product_id.name, supplieri.name.name, supplierinfo.origin_country_id.name, supplieri.origin_country_id.name))
        return True


    _constraints = [
        (_same_supplier_same_origin, "error msg in raise", ['origin_country_id', 'name', 'product_id'])]

product_supplierinfo()
