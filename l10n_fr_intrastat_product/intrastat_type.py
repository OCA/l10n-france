# -*- encoding: utf-8 -*-
##############################################################################
#
#    Report intrastat base module for OpenERP
#    Copyright (C) 2010-2014 Akretion (http://www.akretion.com/)
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

# TODO : put transaction code as False when is_fiscal_only

# If you modify the line below, please also update intrastat_type_view.xml
# (form view of report.intrastat.type, field transaction_code
fiscal_only_tuple = ('25', '26', '31')


class report_intrastat_type(orm.Model):
    _name = "report.intrastat.type"
    _description = "Intrastat type"
    _order = "procedure_code, transaction_code"


    def _compute_readonly_fields(self, cr, uid, procedure_code, context=None):
        res = {}
        if procedure_code in ('19', '29'):
            res['fiscal_value_multiplier'] = 0
        elif procedure_code == '25':
            res['fiscal_value_multiplier'] = -1
        else:
            res['fiscal_value_multiplier'] = 1
        if procedure_code in fiscal_only_tuple:
            res['is_fiscal_only'] = True
        else:
            res['is_fiscal_only'] = False
        if procedure_code in ('11', '19', '29'):
            res['is_vat_required'] = False
        else:
            res['is_vat_required'] = True
        if procedure_code in ('11', '19'):
            res['intrastat_product_type'] = 'import'
        else:
            res['intrastat_product_type'] = 'export'
        return res


    def _compute_all(self, cr, uid, ids, name, arg, context=None):
        result = {}
        for intr_type in self.read(cr, uid, ids, ['id', 'procedure_code'], context=context):
            result[intr_type['id']] = self._compute_readonly_fields(cr, uid, intr_type['procedure_code'], context=context)
        #print "result =", result
        return result


    _columns = {
        'name': fields.char(
            'Name', size=64, required=True,
            help="Description of the Intrastat type."),
        'active': fields.boolean('Active', help="The active field allows you to hide the Intrastat type without deleting it."),
        'object_type': fields.selection([
            ('out_invoice', 'Customer Invoice'),
            ('in_invoice', 'Supplier Invoice'),
            ('out_refund', 'Customer Refund'),
            ('none', 'None'),
        ], 'Possible on', select=True, required=True),
        'procedure_code': fields.selection([
            ('11', "11. Acquisitions intracomm. taxables en France"),
            ('19', "19. Autres introductions"),
            ('21', "21. Livraisons intracomm. exo. en France et taxables dans l'Etat d'arrivée"),
            ('25', "25. Régularisation commerciale - minoration de valeur"),
            ('26', "26. Régularisation commerciale - majoration de valeur"),
            ('29', "29. Autres expéditions intracomm. : travail à façon, réparation..."),
            ('31', "31. Refacturation dans le cadre d'une opération triangulaire")
            ], 'Procedure code', required=True, help="For the 'DEB' declaration to France's customs administration, you should enter the 'code régime' here."),
        'transaction_code': fields.selection([
            ('', '-'),
            ('11', '11'), ('12', '12'), ('13', '13'), ('14', '14'), ('19', '19'),
            ('21', '21'), ('22', '22'), ('23', '23'), ('29', '29'),
            ('30', '30'),
            ('41', '41'), ('42', '42'),
            ('51', '51'), ('52', '52'),
            ('70', '70'),
            ('80', '80'),
            ('91', '91'), ('99', '99'),
            ], 'Transaction code', help="For the 'DEB' declaration to France's customs administration, you should enter the number 'nature de la transaction' here."),
        'is_fiscal_only': fields.function(_compute_all, multi="akretionrules", type='boolean', string='Is fiscal only ?', store={
            'report.intrastat.type': (lambda self, cr, uid, ids, c={}: ids, ['procedure_code'], 10),
                }, help="Only fiscal data should be provided for this procedure code."),
        'fiscal_value_multiplier': fields.function(_compute_all, multi="akretionrules", type='integer', string='Fiscal value multiplier', store={
            'report.intrastat.type': (lambda self, cr, uid, ids, c={}: ids, ['procedure_code'], 10),
                }, help="'0' for procedure codes 19 and 29, '-1' for procedure code 25, '1' for all the others. This multiplier is used to compute the total fiscal value of the declaration."),
        'is_vat_required': fields.function(_compute_all, multi="akretionrules", type='boolean', string='Is partner VAT required?', store={
            'report.intrastat.type': (lambda self, cr, uid, ids, c={}: ids, ['procedure_code'], 10),
                }, help='True for all procedure codes except 11, 19 and 29. When False, the VAT number should not be filled in the Intrastat product line.'),
        'intrastat_product_type': fields.function(_compute_all, type='char', size=10, multi="akretionrules", string='Intrastat product type', store={
            'report.intrastat.type': (lambda self, cr, uid, ids, c={}: ids, ['procedure_code'], 10),
                }, help="Decides on which kind of Intrastat product report ('Import' or 'Export') this Intrastat type can be selected."),
    }

    _defaults = {
        'active': True,
    }

    _sql_constraints = [
        ('code_invoice_type_uniq', 'unique(procedure_code, transaction_code)', 'The pair (procedure code, transaction code) must be unique.'),
    ]

    def real_code_check(self, codes):
        if not codes['procedure_code']:
            raise orm.except_orm(_('Error :'), _('You must enter a value for the procedure code.'))
        if not codes['procedure_code'].isdigit():
            raise orm.except_orm(_('Error :'), _('Procedure code must be a number.'))
        if len(codes['procedure_code']) != 2:
            raise orm.except_orm(_('Error :'), _('Procedure code must have 2 digits.'))
        if codes['transaction_code']:
            if not codes['transaction_code'].isdigit():
                raise orm.except_orm(_('Error :'), _('Transaction code must be a number.'))
            if len(codes['transaction_code']) != 2:
                raise orm.except_orm(_('Error :'), _('Transaction code must have 2 digits.'))
        return True


    def _code_check(self, cr, uid, ids):
        for intrastat_type in self.read(cr, uid, ids, ['procedure_code', 'transaction_code', 'is_fiscal_only', 'object_type']):
            self.real_code_check(intrastat_type)
            if intrastat_type['object_type'] == 'out' and intrastat_type['procedure_code'] != '29':
                raise orm.except_orm(_('Error :'), _("Procedure code must be '29' for an Outgoing products."))
            elif intrastat_type['object_type'] == 'in' and intrastat_type['procedure_code'] != '19':
                raise orm.except_orm(_('Error :'), _("Procedure code must be '19' for an Incoming products."))
            if intrastat_type['procedure_code'] not in fiscal_only_tuple and not intrastat_type['transaction_code']:
                raise orm.except_orm(_('Error :'), _('You must enter a value for the transaction code.'))
            if intrastat_type['procedure_code'] in fiscal_only_tuple and intrastat_type['transaction_code']:
                raise orm.except_orm(_('Error :'), _("You should not set a transaction code when the Procedure code is '25', '26' or '31'."))
        return True

    _constraints = [
        (_code_check, "Error msg in raise", ['procedure_code', 'transaction_code']),
    ]

    def procedure_code_on_change(
            self, cr, uid, ids, procedure_code=False, context=None):
        result = {}
        result['value'] = {}
        if procedure_code in fiscal_only_tuple:
            result['value'].update({'transaction_code': False})
        result['value'].update(
            self._compute_readonly_fields(cr, uid, procedure_code))
        return result
